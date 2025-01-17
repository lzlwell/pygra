from __future__ import print_function
import numpy as np
import scipy.linalg as lg
from . import multicell
from . import algebra


#try:
#  import greenf90
#  use_fortran = True
#except:
#  use_fortran=False
#  print("Ups, FORTRAN not working in, green.py")

use_fortran = False

try: from .gauss_invf90 import gauss_inv as ginv
except: 
  pass
#    print("FORTRAN gauss routines not ok in green.py")


class gf_convergence():
   """ Class to manage the convergence  options
   of the green functions """
   optimal = False
   refinement = False
   guess = True # use old green function
   def __init__(self,mode):
     if mode=="fast":   # fast mode,used for coule to finite systems 
       self.eps = 0.001
       self.max_error = 1.0
       self.num_rep = 10
       self.mixing = 1.0
     if mode=="lead":
       self.eps = 0.001
       self.max_error = 0.00001
       self.num_rep = 3
       self.mixing = 0.8
     if mode=="hundred":  
       self.eps = 0.001
       self.max_error = 1.0
       self.num_rep = 100
       self.mixing = 1.0



def dyson(intra,inter,energy=0.0,gf=None,is_sparse=False,initial = None):
  """ Solves the dyson equation for a one dimensional
  system with intra matrix 'intra' and inter to the nerest cell
  'inter'"""
  # get parameters
  if gf is None: gf = gf_convergence("lead")
  mixing = gf.mixing
  eps = gf.eps
  max_error = gf.max_error
  num_rep = gf.num_rep
  optimal = gf.optimal
  try:
    intra = intra.todense()
    inter = inter.todense()
  except:
    a = 1
  if initial is None:  # if green not provided. initialize at zero
    from numpy import zeros
   
    g_guess = intra*0.0j
  else:
    g_guess = initial
  # calculate using fortran
  if optimal:
    print("Fortran dyson calculation")
    from .green_fortran import dyson  # import fortran subroutine
    (g,num_redo) = dyson(intra,inter,energy,num_rep,mixing=mixing,
               eps=eps,green_guess=g_guess,max_error=max_error)
    print("      Converged in ",num_redo,"iterations\n")
    from numpy import matrix
    g = matrix(g)
  # calculate using python
  if not optimal:
    g_old = g_guess # first iteration
    iden = np.matrix(np.identity(len(intra),dtype=complex)) # create identity
    e = iden*(energy+1j*eps) # complex energy
    while True: # loop over iterations
      self = inter@g_old@inter.H # selfenergy
      g = (e - intra - self).I # dyson equation
      if np.max(np.abs(g-g_old))<gf.max_error: break
      g_old = mixing*g + (1.-mixing)*g_old # new green function
  if is_sparse: 
    from scipy.sparse import csc_matrix
    g = csc_matrix(g)
  return g











def dos_infinite(intra,inter,energies=[0.0],num_rep=100,
                      mixing=0.7,eps=0.0001,green_guess=None,max_error=0.0001):
   """ Calculates the surface density of states by using a 
    green function approach"""
   dos = [] # list with the density of states
   iden = np.matrix(np.identity(len(intra),dtype=complex)) # create idntity
   for energy in energies: # loop over energies
     # right green function
     gr = dyson(intra,inter,energy=energy,num_rep=num_rep,mixing=mixing,
          eps=eps,green_guess=green_guess,max_error=max_error)
     # left green function
     gl = dyson(intra,inter.H,energy=energy,num_rep=num_rep,mixing=mixing,
          eps=eps,green_guess=green_guess,max_error=max_error)
     # central green function
     selfl = inter.H@gl@inter # left selfenergy
     selfr = inter@gr@inter.H # right selfenergy
     gc = energy*iden -intra -selfl -selfr # dyson equation for the center
     gc = gc.I # calculate inverse
     dos.append(-gc.trace()[0,0].imag)  # calculate the trace of the Green function
   return dos




def dos_semiinfinite(intra,inter,energies=np.linspace(-1.0,1.0,100),num_rep=100,
                      mixing=0.7,eps=0.0001,green_guess=None,max_error=0.0001):
   """ Calculates the surface density of states by using a 
    green function approach"""
   dos = [] # list with the density of states
   for energy in energies: # loop over energies
#     gf = dyson(intra,inter,energy=energy,num_rep=num_rep,mixing=mixing,
     gb,gf = green_renormalization(intra,inter,energy=energy,delta=delta)
     dos.append(-gf.trace()[0,0].imag)  # calculate the trace of the Green function
   return energies,dos









def dos_heterostructure(hetero,energies=[0.0],num_rep=100,
                      mixing=0.7,eps=0.0001,green_guess=None,max_error=0.0001):
   """ Calculates the density of states 
       of a heterostructure by a  
    green function approach, input is a heterostructure class"""
   dos = [] # list with the density of states
   iden = np.matrix(np.identity(len(intra),dtype=complex)) # create idntity
   for energy in energies: # loop over energies
     # right green function
     intra = hetero.right_intra
     inter = hetero.right_inter
     gr = dyson(intra,inter,energy=energy,num_rep=num_rep,mixing=mixing,
          eps=eps,green_guess=green_guess,max_error=max_error)
     # left green function
     intra = hetero.right_intra
     inter = hetero.right_inter
     gl = dyson(intra,inter,energy=energy,num_rep=num_rep,mixing=mixing,
          eps=eps,green_guess=green_guess,max_error=max_error)
     # central green function
     selfl = inter.H@gl@inter # left selfenergy
     selfr = inter@gr@inter.H # right selfenergy
     gc = energy*iden -intra -selfl -selfr # dyson equation for the center
     gc = gc.I # calculate inverse
     dos.append(-gc.trace()[0,0].imag)  # calculate the trace of the Green function
   return dos



def read_matrix(f):
  """Read green function from a file"""
  m = np.genfromtxt(f)
  d = int(max(m.transpose()[0]))+1 # dimension of the green functions
  g = np.matrix([[0.0j for i in range(d)] for j in range(d)]) # create matrix
  for r in m:
    i = int(r[0])
    j = int(r[1])
    ar = r[2]
    ai = r[3]
    g[i,j] = ar +1j*ai # store element
  return g # return green function



def write_matrix(f,g):
  """Write green function from a file"""
  fw = open(f,"w") # open file to write
  n = len(g) # dimension of the matrix
  for i in range(n):
    for j in range(n):
      fw.write(str(i)+"  ")
      fw.write(str(j)+"  ")
      fw.write(str(g[i,j].real)+"  ")
      fw.write(str(g[i,j].imag)+"\n")
  fw.close()   # close file


# detect non vanishing elements of a matrix
def nv_el(m):
  """ get the non vanishing elments of a matrix"""
  from scipy.sparse import csc_matrix as csc
  mc = csc(m) # to coo_matrixi
  mc.eliminate_zeros()
  mc = mc.tocoo()
  data = mc.data # get data
  col = mc.col # get column index
  row = mc.row # get row index
  nv = []
  nt=len(data)
  for i in range(nt):
   # save the nonvanishing values
   nv.append([row[i]+1,col[i]+1,data[i].real,data[i].imag])
  return nv


def write_sparse(f,g):
  """ Write a sparse matrix in a file"""
  fw = open(f,"w") # open the file
  fw.write("# dimension = "+str(g.shape[0])+"\n")
  nv=nv_el(g)
  for iv in range(len(nv)):
    fw.write(str(int(nv[iv][0]))+'   ')
    fw.write(str(int(nv[iv][1]))+'   ')
    fw.write('{0:.8f}'.format(float(nv[iv][2]))+'   ')
    fw.write('{0:.8f}'.format(float(nv[iv][3]))+'   ')
    fw.write('  !!!  i  j   Real   Imag\n')
  fw.close()




def read_sparse(f,sparse=True):
  """Read green function from a file"""
  l = open(f,"r").readlines()[0] # first line
  d = int(l.split("=")[1])
  m = np.genfromtxt(f)
  if not sparse:
# create matrix  
    g = np.matrix([[0.0j for i in range(d)] for j in range(d)]) 
    for r in m:
      i = int(r[0])-1
      j = int(r[1])-1
      ar = r[2]
      ai = r[3]
      g[i,j] = ar +1j*ai # store element
  if sparse:
    from scipy.sparse import coo_matrix
    g = coo_matrix([[0.0j for i in range(d)] for j in range(d)]) 
    row = np.array([0 for i in range(len(m))])
    col = np.array([0 for i in range(len(m))])
    data = np.array([0j for i in range(len(m))])
    for i in range(len(m)):
      r = m[i]
      row[i] = int(r[0])-1
      col[i] = int(r[1])-1
      ar = r[2]
      ai = r[3]
      data[i] = ar +1j*ai # store element
    g.col = col
    g.row = row
    g.data = data
  return g # return green function





def gauss_inverse(m,i=0,j=0,test=False):
  try: from .gauss_invf90 import gauss_inv as ginv
  except: 
    test = True # Ups, this might blow up
  """ Calculates the inverso of a block diagonal
      matrix """
  if test: # check whether the inversion worked 
    return block_inverse(m,i=i,j=j)
  nb = len(m) # number of blocks
  ca = [None for ii in range(nb)]
  ua = [None for ii in range(nb-1)]
  da = [None for ii in range(nb-1)]
  for ii in range(nb): # diagonal part
    ca[ii] = m[ii][ii]
  for ii in range(nb-1):
    ua[ii] = m[ii][ii+1]
    da[ii] = m[ii+1][ii]
  # in case you use the -1 notation of python
  if i<0: i += nb 
  if j<0: j += nb 
  # now call the actual fortran routine
  mout = ginv(ca,da,ua,i+1,j+1)
  mout = np.matrix(mout)
  return mout




def block_inverse(m,i=0,j=0):
  """ Calculate a certain element of the inverse of a block matrix"""
  from scipy.sparse import csc_matrix,bmat
  nb = len(m) # number of blocks
  if i<0: i += nb 
  if j<0: j += nb 
  mt = [[None for ii in range(nb)] for jj in range(nb)]
  for ii in range(nb): # diagonal part
    mt[ii][ii] = csc_matrix(m[ii][ii])
  for ii in range(nb-1):
    mt[ii][ii+1] = csc_matrix(m[ii][ii+1])
    mt[ii+1][ii] = csc_matrix(m[ii+1][ii])
  mt = bmat(mt).todense() # create dense matrix
  # select which elements you need
  ilist = [m[ii][ii].shape[0] for ii in range(i)] 
  jlist = [m[jj][jj].shape[1] for jj in range(j)] 
  imin = sum(ilist)
  jmin = sum(jlist)
  mt = mt.I # calculate inverse
  imax = imin + m[i][i].shape[0]
  jmax = jmin + m[j][j].shape[1]
  mo = [ [mt[ii,jj] for jj in range(jmin,jmax)] for ii in range(imin,imax) ] 
  mo = np.matrix(mo)
  return mo




def green_renormalization(intra,inter,energy=0.0,nite=None,
                            error=0.000001,info=False,delta=0.001,
                            use_fortran = use_fortran):
  """ Calculates bulk and surface Green function by a renormalization
  algorithm, as described in I. Phys. F: Met. Phys. 15 (1985) 851-858 """
  error = delta/100
  if use_fortran: # use the fortran implementation
    (ge,gb) = greenf90.renormalization(intra,inter,energy,error,delta)
    return np.matrix(gb),np.matrix(ge)
  else:
    e = np.matrix(np.identity(intra.shape[0])) * (energy + 1j*delta)
    ite = 0
    alpha = inter.copy()
    beta = inter.H.copy()
    epsilon = intra.copy()
    epsilon_s = intra.copy()
    while True: # implementation of Eq 11
      einv = (e - epsilon).I # inverse
      epsilon_s = epsilon_s + alpha @ einv @ beta
      epsilon = epsilon + alpha * einv @ beta + beta @ einv @ alpha
      alpha = alpha @ einv @ alpha  # new alpha
      beta = beta @ einv @ beta  # new beta
      ite += 1
      # stop conditions
      if not nite is None:
        if ite > nite:  break 
      else:
        if np.max(np.abs(alpha))<error and np.max(np.abs(beta))<error: break
    if info:
      print("Converged in ",ite,"iterations")
    g_surf = (e - epsilon_s).I # surface green function
    g_bulk = (e - epsilon).I  # bulk green function 
    return g_bulk,g_surf



def bloch_selfenergy(h,nk=100,energy = 0.0, delta = 0.01,mode="full",
                         error=0.00001):
  """ Calculates the selfenergy of a cell defect,
      input is a hamiltonian class"""
  if mode=="adaptative": mode = "adaptive"
  def gr(ons,hop):
    """ Calculates G by renormalization"""
    gf,sf = green_renormalization(ons,hop,energy=energy,nite=None,
                            error=error,info=False,delta=delta)
    return gf,sf
  hk_gen = h.get_hk_gen()  # generator of k dependent hamiltonian
  if h.is_multicell: 
    mode = "full" # multicell hamiltonians only have full mode
    print("Changed to full mode in selfenergy")
  d = h.dimensionality # dimensionality of the system
  g = h.intra *0.0j # initialize green function
  e = np.matrix(np.identity(len(g)))*(energy + delta*1j) # complex energy
  if mode=="full":  # full integration
    if d==1: # one dimensional
      ks = [[k,0.,0.] for k in np.linspace(0.,1.,nk,endpoint=False)]
    elif d==2: # two dimensional
      ks = []
      kk = np.linspace(0.,1.,nk,endpoint=False)  # interval 0,1
      for ikx in kk:
        for iky in kk:
          ks.append([ikx,iky,0.])
      ks = np.array(ks)  # all the kpoints
    else: raise # raise error
    for k in ks:  # loop in BZ
      g += (e - hk_gen(k)).I  # add green function  
    g = g/len(ks)  # normalize
  #####################################################
  #####################################################
  if mode=="renormalization":
    if d==1: # full renormalization
      g,s = gr(h.intra,h.inter)  # perform renormalization
    elif d==2: # two dimensional, loop over k's
      ks = [[k,0.,0.] for k in np.linspace(0.,1.,nk,endpoint=False)]
      for k in ks:  # loop over k in y direction
 # add contribution to green function
        g += green_kchain(h,k=k,energy=energy,delta=delta,error=error) 
      g = g/len(ks)
    else: raise
  #####################################################
  #####################################################
  if mode=="adaptive":
    if d==1: # full renormalization
      g,s = gr(h.intra,h.inter)  # perform renormalization
    elif d==2: # two dimensional, loop over k's
      ks = [[k,0.,0.] for k in np.linspace(0.,1.,nk,endpoint=False)]
#      ks = np.linspace(0.,1.,nk,endpoint=False) 
      from . import integration
      def fint(k):
        """ Function to integrate """
        return green_kchain(h,k=[k,0.,0.],energy=energy,
                delta=delta,error=error) 
      # eps is error, might work....
      g = integration.integrate_matrix(fint,xlim=[0.,1.],eps=error) 
        # chain in the y direction
    else: raise
  # now calculate selfenergy
  selfenergy = e - h.intra - g.I
  return g,selfenergy




def get1dhamiltonian(hin,k=[0.0,0.,0.],reverse=False):
  """Return onsite and hopping matrix for a 1D Hamiltonian"""
  from . import multicell
#  h = hin.copy() # copy Hamiltonian
#  if h.dimensionality != 2: raise # only for 2d
#  if h.is_multicell: # multicell Hamiltonian
#    h = multicell.turn_no_multicell(h) # convert into a normal Hamiltonian
#  tky = h.ty*np.exp(1j*np.pi*2.*k)
#  tkxy = h.txy*np.exp(1j*np.pi*2.*k)
#  tkxmy = h.txmy*np.exp(-1j*np.pi*2.*k)  # notice the minus sign !!!!
  # chain in the x direction
#  ons = h.intra + tky + tky.H  # intra of k dependent chain
#  hop = h.tx + tkxy + tkxmy  # hopping of k-dependent chain
  (ons,hop) = multicell.kchain(hin,k=k)
  if reverse: return (ons,algebra.hermitian(hop)) # return 
  else: return (ons,hop) # return 
  




def green_kchain(h,k=0.,energy=0.,delta=0.01,only_bulk=True,
                    error=0.0001,hs=None,reverse=False):
  """ Calculates the green function of a kdependent chain for a 2d system """
  def gr(ons,hop):
    """ Calculates G by renormalization"""
    gf,sf = green_renormalization(ons,hop,energy=energy,nite=None,
                            error=error,info=False,delta=delta)
    if hs is not None: # surface matrix provided
      ez = (energy+1j*delta)*np.identity(h.intra.shape[0]) # energy
      sigma = hop@sf@hop.H # selfenergy
      if callable(hs): ons2 = hs(k)
      else: ons2 = hs
      sf = (ez - ons2 - sigma).I # return Dyson
    if only_bulk:  return gf
    else:  return gf,sf
  (ons,hop) = get1dhamiltonian(h,k,reverse=reverse) # get 1D Hamiltonian
  return gr(ons,hop)  # return green function



def green_surface_cells(gs,hop,ons,delta=1e-2,e=0.0,n=0):
    """Compute the surface Green's function for several unit cells"""
    hopH = algebra.H(hop) # Hermitian
    ez = (e+1j*delta)*np.identity(ons.shape[0]) # energy
    gt = np.zeros(ons.shape[0],dtype=np.complex) # energy
    sigmar = hop@gs@algebra.H(hop) # of the infinite right part
    out = []
    for i in range(n):
      sigmal = algebra.H(hop)@gt@hop # selfenergy
      # couple infinite right to finite left
      gemb = algebra.inv(ez - ons - sigmal- sigmar) # full dyson equation
      # compute surface spectral function of the left block only
      gt = algebra.inv(ez - ons - sigmal) # return Dyson equation
      out.append(gemb) # store this green's function
    return out # return green's functions



def green_kchain_evaluator(h,k=0.,delta=0.01,only_bulk=True,
                    error=0.0001,hs=None,reverse=False):
  """ Calculates the green function of a kdependent chain for a 2d system """
  def gr(ons,hop,energy):
    """ Calculates G by renormalization"""
    gf,sf = green_renormalization(ons,hop,energy=energy,nite=None,
                            error=error,info=False,delta=delta)
#    print(hs)
    if hs is not None: # surface matrix provided
      ez = (energy+1j*delta)*np.identity(h.intra.shape[0]) # energy
      sigma = hop@sf@hop.H # selfenergy
      if callable(hs): ons2 = ons + hs(k)
      else: ons2 = ons + hs
      sf = algebra.inv(ez - ons2 - sigma) # return Dyson
    # which green function to return
    if only_bulk:  return gf
    else:  return gf,sf
  (ons,hop) = get1dhamiltonian(h,k,reverse=reverse) # get 1D Hamiltonian
  def fun(energy): # evaluator
    return gr(ons,hop,energy)  # return green function
  return fun # return the function















def interface(h1,h2,k=[0.0,0.,0.],energy=0.0,delta=0.01):
  """Get the Green function of an interface"""
  from scipy.sparse import csc_matrix as csc
  from scipy.sparse import bmat
  gs1,sf1 = green_kchain(h1,k=k,energy=energy,delta=delta,
                   only_bulk=False,reverse=True) # surface green function 
  gs2,sf2 = green_kchain(h2,k=k,energy=energy,delta=delta,
                   only_bulk=False,reverse=False) # surface green function 
  #############
  ## 1  C  2 ##
  #############
  # Now apply the Dyson equation
  (ons1,hop1) = get1dhamiltonian(h1,k,reverse=True) # get 1D Hamiltonian
  (ons2,hop2) = get1dhamiltonian(h2,k,reverse=False) # get 1D Hamiltonian
  havg = (hop1.H + hop2)/2. # average hopping
  ons = bmat([[csc(ons1),csc(havg)],[csc(havg.H),csc(ons2)]]) # onsite
  self2 = bmat([[csc(ons1)*0.0,None],[None,csc(hop2@sf2@hop2.H)]])
  self1 = bmat([[csc(hop1@sf1@hop1.H),None],[None,csc(ons2)*0.0]])
  # Dyson equation
  ez = (energy+1j*delta)*np.identity(ons1.shape[0]+ons2.shape[0]) # energy
  ginter = (ez - ons - self1 - self2).I # Green function
  # now return everything, first, second and hybrid
  return (gs1,sf1,gs2,sf2,ginter)


def interface_multienergy(h1,h2,k=[0.0,0.,0.],energies=[0.0],delta=0.01,
        dh1=None,dh2=None):
  """Get the Green function of an interface"""
  from scipy.sparse import csc_matrix as csc
  from scipy.sparse import bmat
  fun1 = green_kchain_evaluator(h1,k=k,delta=delta,hs=None,
                   only_bulk=False,reverse=True) # surface green function 
  fun2 = green_kchain_evaluator(h2,k=k,delta=delta,hs=None,
                   only_bulk=False,reverse=False) # surface green function 
  out = [] # output
  for energy in energies: # loop
    gs1,sf1 = fun1(energy)
    gs2,sf2 = fun2(energy)
    #############
    ## 1  C  2 ##
    #############
    # Now apply the Dyson equation
    (ons1,hop1) = get1dhamiltonian(h1,k,reverse=True) # get 1D Hamiltonian
    (ons2,hop2) = get1dhamiltonian(h2,k,reverse=False) # get 1D Hamiltonian
    havg = (hop1.H + hop2)/2. # average hopping
    if dh1 is not None: ons1 = ons1 + dh1
    if dh2 is not None: ons2 = ons2 + dh2
    ons = bmat([[csc(ons1),csc(havg)],[csc(havg.H),csc(ons2)]]) # onsite
    self2 = bmat([[csc(ons1)*0.0,None],[None,csc(hop2@sf2@hop2.H)]])
    self1 = bmat([[csc(hop1@sf1@hop1.H),None],[None,csc(ons2)*0.0]])
    # Dyson equation
    ez = (energy+1j*delta)*np.identity(ons1.shape[0]+ons2.shape[0]) # energy
    ginter = (ez - ons - self1 - self2).I # Green function
    # now return everything, first, second and hybrid
    out.append([gs1,sf1,gs2,sf2,ginter])
  return out # return output





def surface_multienergy(h1,k=[0.0,0.,0.],energies=[0.0],**kwargs):
  """Get the Green function of an interface"""
  from scipy.sparse import csc_matrix as csc
  from scipy.sparse import bmat
  fun1 = green_kchain_evaluator(h1,k=k,
                   only_bulk=False,reverse=True,
                   **kwargs) # surface green function 
  out = [] # output
  for energy in energies: # loop
    gs1,sf1 = fun1(energy)
    out.append([sf1,gs1])
  return out # return output















def supercell_selfenergy(h,e=0.0,delta=0.001,nk=100,nsuper=[1,1]):
  """alculates the selfenergy of a certain supercell """
  try:   # if two number given
    nsuper1 = nsuper[0]
    nsuper2 = nsuper[1]
  except: # if only one number given
    nsuper1 = nsuper
    nsuper2 = nsuper
  print("Supercell",nsuper1,"x",nsuper2)
  ez = e + 1j*delta # create complex energy
  from . import dyson2d
  g = dyson2d.dyson2d(h.intra,h.tx,h.ty,h.txy,h.txmy,nsuper1,nsuper2,300,ez)
  g = np.matrix(g) # convert to matrix
  n = nsuper1*nsuper2 # number of cells
  intrasuper = [[None for j in range(n)] for i in range(n)]
  # create indexes (same order as in fortran routine)
  k = 0
  inds = []
  for i in range(nsuper1):
    for j in range(nsuper2):
      inds += [(i,j)]
      k += 1 
  # create hamiltonian of the supercell
  from scipy.sparse import bmat
  from scipy.sparse import csc_matrix as csc
  tx = csc(h.tx)
  ty = csc(h.ty)
  txy = csc(h.txy)
  txmy = csc(h.txmy)
  intra = csc(h.intra)
  for i in range(n):
    intrasuper[i][i] = intra # intracell
    (x1,y1) = inds[i]
    for j in range(n):
      (x2,y2) = inds[j]
      dx = x2-x1
      dy = y2-y1
      if dx==1 and  dy==0: intrasuper[i][j] = tx  
      if dx==-1 and dy==0: intrasuper[i][j] = tx.H  
      if dx==0 and  dy==1: intrasuper[i][j] = ty  
      if dx==0 and  dy==-1: intrasuper[i][j] = ty.H  
      if dx==1 and  dy==1: intrasuper[i][j] = txy 
      if dx==-1 and dy==-1: intrasuper[i][j] = txy.H 
      if dx==1 and  dy==-1: intrasuper[i][j] = txmy  
      if dx==-1 and dy==1: intrasuper[i][j] = txmy.H  
  intrasuper = bmat(intrasuper).todense() # supercell
  eop = np.matrix(np.identity(len(g),dtype=np.complex))*(ez)
  selfe = eop - intrasuper - g.I
  return g,selfe







def green_generator(h,nk=20):
  """Returns a function capable of calculating the Green function
  at a certain energy, by explicity summing the k-dependent Green functions"""
  if h.dimensionality != 2: raise # only for 2d
  shape = h.intra.shape # shape
  hkgen = h.get_hk_gen() # get the Hamiltonian generator
  wfs = np.zeros((nk*nk,shape[0],shape[0]),dtype=np.complex) # allocate vector
  es = np.zeros((nk*nk,shape[0])) # allocate vector, energies
  ks = np.zeros((nk*nk,2)) # allocate vector, energies
  ii = 0 # counter
  for ik in np.linspace(0.,1.,nk,endpoint=False): # loop
    for jk in np.linspace(0.,1.,nk,endpoint=False): # loop
      estmp,wfstmp = lg.eigh(hkgen([ik,jk])) # get eigens
#      estmp,wfstmp = lg.eigh(hkgen(np.random.random(2))) # get eigens
      es[ii,:] = estmp.copy() # copy
      ks[ii,:] = np.array([ik,jk]) # store
      wfs[ii,:,:] = wfstmp.transpose().copy() # copy
      ii += 1 # increase counter
  # All the wavefunctions have been calculate
  # Now create the output function
  from scipy.integrate import simps
  def getgreen(energy,delta=0.001):
    """Return the Green function"""
    delta = 2./nk
#    store = np.zeros((nk*nk,shape),dtype=np.complex) # storage array
    zero = np.matrix(np.zeros(shape),dtype=np.complex) # zero matrix
    for ii in range(nk*nk): # loop over kpoints
      v = energy + delta*1j - es[ii,:] # array
      C = np.matrix(np.diag(1./v)) # matrix
      A = np.matrix(wfs[ii,:,:]) # get the matrix with wavefunctions
#      store[ii,:,:] = A.H*C*A # store contribution
      zero += A.H@C@A # add contribution
#    for i in range(shape[0]): # loop 
#      for j in range(shape[0]): # loop 
#        m = store[:,i,j].reshape((nk,nk)) # transform into a grid
#        zero[i,j] =  # normalize
    zero /= nk*nk # normalize
    ediag = np.matrix(np.identity(shape[0]))*(energy + delta*1j)
    selfenergy = ediag - h.intra - zero.I
    return zero,selfenergy
  return getgreen # return function



def green_operator(h0,operator,e=0.0,delta=1e-3,nk=10):
    """Return the integration of an operator times the Green function"""
    h = h0.copy()
    h.turn_dense()
    hkgen = h.get_hk_gen() # get generator
    iden = np.identity(h.intra.shape[0],dtype=np.complex)
    from . import klist
    ks = klist.kmesh(h.dimensionality,nk=nk) # klist
    out = 0.0 # output
    if callable(operator): # callable operator
      for k in ks: # loop over kpoints
        hk = hkgen(k) # Hamiltonian
        o0 = lg.inv(iden*(e+1j*delta) - hk) # Green's function
        if callable(operator): o1 = operator(k)
        else: o1 = operator
        out += -(o0@o1).trace().imag # Add contribution
      out /= len(ks) # normalize
    else:
      g = bloch_selfenergy(h,energy=e,delta=delta,mode="adaptive")[0] 
      out = -(np.array(g)@operator).trace().imag
    return out



def GtimesO(g,o,k=[0.,0.,0.]):
    """Green function times operator"""
    o = algebra.todense(o) # convert to dense operator if possible
    if o is None: return g # return Green function
    elif type(o)==type(g): return g@o # return
    elif callable(o): return o(g,k=k) # call the operator
    else:
        print(type(g),type(o))
        raise



