# library to deal with the spectral properties of the hamiltonian
import numpy as np
import scipy.linalg as lg
import scipy.sparse.linalg as slg
import os
from .operators import operator2list
from . import parallel
from . import kpm
from . import timing
from . import algebra

from .fermisurface import multi_fermi_surface

arpack_tol = 1e-5
arpack_maxiter = 10000

def fermi_surface(h,write=True,output_file="FERMI_MAP.OUT",
                    e=0.0,nk=50,nsuper=1,reciprocal=True,
                    delta=None,refine_delta=1.0,operator=None,
                    mode='full',num_waves=2,info=True):
  """Calculates the Fermi surface of a 2d system"""
  if operator is None:
    operator = np.matrix(np.identity(h.intra.shape[0]))
  if h.dimensionality!=2: raise  # continue if two dimensional
  hk_gen = h.get_hk_gen() # gets the function to generate h(k)
  kxs = np.linspace(-nsuper,nsuper,nk)  # generate kx
  kys = np.linspace(-nsuper,nsuper,nk)  # generate ky
  iden = np.identity(h.intra.shape[0],dtype=np.complex)
  kxout = []
  kyout = []
  if reciprocal: R = h.geometry.get_k2K() # get matrix
  else:  R = np.matrix(np.identity(3)) # get identity
  # setup a reasonable value for delta
  if delta is None:
 #   delta = 1./refine_delta*2.*np.max(np.abs(h.intra))/nk
    delta = 1./refine_delta*2./nk

  #### function to calculate the weight ###
  if mode=='full': # use full inversion
    def get_weight(hk):
      gf = ((e+1j*delta)*iden - hk).I # get green function
      if callable(operator):
        tdos = -(operator(x,y)*gf).imag # get imaginary part
      else: tdos = -(operator*gf).imag # get imaginary part
      return tdos.trace()[0,0].real # return traze
  elif mode=='lowest': # use full inversion
    def get_weight(hk):
      es,waves = slg.eigsh(hk,k=num_waves,sigma=e,tol=arpack_tol,which="LM",
                            maxiter = arpack_maxiter)
      return np.sum(delta/((e-es)**2+delta**2)) # return weight
  else: raise

##############################################


  ts = timing.Testimator()
  # setup the operator
  rs = [] # empty list
  for x in kxs:
    for y in kxs:
      rs.append([x,y,0.]) # store
  def getf(r): # function to compute FS
      rm = np.matrix(r).T
      k = np.array((R*rm).T)[0] # change of basis
      hk = hk_gen(k) # get hamiltonian
      return get_weight(hk)
  rs = np.array(rs) # transform into array
  from . import parallel
  kxout = rs[:,0] # x coordinate
  kyout = rs[:,1] # y coordinate
  if parallel.cores==1: # serial execution
      kdos = [] # empty list
      for r in rs: # loop
        if info: print("Doing",r)
        kdos.append(getf(r)) # add to the list
  else: # parallel execution
      kdos = parallel.pcall(getf,rs) # compute all
  if write:  # optionally, write in file
    f = open(output_file,"w") 
    for (x,y,d) in zip(kxout,kyout,kdos):
      f.write(str(x)+ "   "+str(y)+"   "+str(d)+"\n")
    f.close() # close the file
  return (kxout,kyout,d) # return result




def boolean_fermi_surface(h,write=True,output_file="BOOL_FERMI_MAP.OUT",
                    e=0.0,nk=50,nsuper=1,reciprocal=False,
                    delta=None):
  """Calculates the Fermi surface of a 2d system"""
  if h.dimensionality!=2: raise  # continue if two dimensional
  hk_gen = h.get_hk_gen() # gets the function to generate h(k)
  kxs = np.linspace(-nsuper,nsuper,nk)  # generate kx
  kys = np.linspace(-nsuper,nsuper,nk)  # generate ky
  kdos = [] # empty list
  kxout = []
  kyout = []
  if reciprocal: R = h.geometry.get_k2K() # get matrix
  # setup a reasonable value for delta
  if delta is None:
    delta = 8./np.max(np.abs(h.intra))/nk
  for x in kxs:
    for y in kxs:
      r = np.matrix([x,y,0.]).T # real space vectors
      k = np.array((R*r).T)[0] # change of basis
      hk = hk_gen(k) # get hamiltonian
      evals = lg.eigvalsh(hk) # diagonalize
      de = np.abs(evals - e) # difference with respect to fermi
      de = de[de<delta] # energies close to fermi
      if len(de)>0: kdos.append(1.0) # add to the list
      else: kdos.append(0.0) # add to the list
      kxout.append(x)
      kyout.append(y)
  if write:  # optionally, write in file
    f = open(output_file,"w") 
    for (x,y,d) in zip(kxout,kyout,kdos):
      f.write(str(x)+ "   "+str(y)+"   "+str(d)+"\n")
    f.close() # close the file
  return (kxout,kyout,d) # return result






















from .bandstructure import braket_wAw


def selected_bands2d(h,output_file="BANDS2D_",nindex=[-1,1],
               nk=50,nsuper=1,reciprocal=True,
               operator=None,k0=[0.,0.]):
  """ Calculate a selected bands in a 2d Hamiltonian"""
  if h.dimensionality!=2: raise  # continue if two dimensional
  hk_gen = h.get_hk_gen() # gets the function to generate h(k)
  kxs = np.linspace(-nsuper,nsuper,nk)+k0[0]  # generate kx
  kys = np.linspace(-nsuper,nsuper,nk)+k0[1]  # generate ky
  kdos = [] # empty list
  kxout = []
  kyout = []
  if reciprocal: R = h.geometry.get_k2K() # get matrix
  else:  R = np.matrix(np.identity(3)) # get identity
  # setup a reasonable value for delta
  # setup the operator
  operator = operator2list(operator) # convert into a list
  os.system("rm -f "+output_file+"*") # delete previous files
  fo = [open(output_file+"_"+str(i)+".OUT","w") for i in nindex] # files        
  for x in kxs:
    for y in kxs:
      print("Doing",x,y)
      r = np.matrix([x,y,0.]).T # real space vectors
      k = np.array((R*r).T)[0] # change of basis
      hk = hk_gen(k) # get hamiltonian
      if not h.is_sparse: evals,waves = lg.eigh(hk) # eigenvalues
      else: evals,waves = slg.eigsh(hk,k=max(nindex)*2,sigma=0.0,
             tol=arpack_tol,which="LM") # eigenvalues
      waves = waves.transpose() # transpose
      epos,wfpos = [],[] # positive
      eneg,wfneg = [],[] # negative
      for (e,w) in zip(evals,waves): # loop
        if e>0.0: # positive
          epos.append(e)
          wfpos.append(w)
        else: # negative
          eneg.append(e)
          wfneg.append(w)
      # now sort the waves
      wfpos = [yy for (xx,yy) in sorted(zip(epos,wfpos))] 
      wfneg = [yy for (xx,yy) in sorted(zip(-np.array(eneg),wfneg))] 
      epos = sorted(epos)
      eneg = -np.array(sorted(-np.array(eneg)))
#      epos = sorted(evals[evals>0]) # positive energies
#      eneg = -np.array(sorted(np.abs(evals[evals<0]))) # negative energies
      for (i,j) in zip(nindex,range(len(nindex))): # loop over desired bands
        fo[j].write(str(x)+"     "+str(y)+"   ")
        if i>0: # positive
          fo[j].write(str(epos[i-1])+"  ")
          for op in operator: # loop over operators
            c = braket_wAw(wfpos[i-1],op).real # expectation value
            fo[j].write(str(c)+"  ") # write in file
          fo[j].write("\n") # write in file
          
        if i<0: # negative
          fo[j].write(str(eneg[abs(i)-1])+"\n")
          for op in operator: # loop over operators
            c = braket_wAw(wfneg[abs(i)-1],op).real # expectation value
            fo[j].write(str(c)+"  ") # write in file
          fo[j].write("\n") # write in file
  [f.close() for f in fo] # close file


get_bands = selected_bands2d




def ev2d(h,nk=50,nsuper=1,reciprocal=False,
               operator=None,k0=[0.,0.],kreverse=False):
  """ Calculate the expectation value of a certain operator"""
  if h.dimensionality!=2: raise  # continue if two dimensional
  hk_gen = h.get_hk_gen() # gets the function to generate h(k)
  kxs = np.linspace(-nsuper,nsuper,nk,endpoint=True)+k0[0]  # generate kx
  kys = np.linspace(-nsuper,nsuper,nk,endpoint=True)+k0[1]  # generate ky
  if kreverse: kxs,kys = -kxs,-kys
  kdos = [] # empty list
  kxout = []
  kyout = []
  if reciprocal: R = h.geometry.get_k2K() # get matrix
  else:  R = np.matrix(np.identity(3)) # get identity
  # setup the operator
  operator = operator2list(operator) # convert into a list
  fo = open("EV2D.OUT","w") # open file
  for x in kxs:
    for y in kxs:
      print("Doing",x,y)
      r = np.matrix([x,y,0.]).T # real space vectors
      k = np.array((R*r).T)[0] # change of basis
      hk = hk_gen(k) # get hamiltonian
      if not h.is_sparse: evals,waves = lg.eigh(hk) # eigenvalues
      else: evals,waves = slg.eigsh(hk,k=max(nindex)*2,sigma=0.0,
             tol=arpack_tol,which="LM") # eigenvalues
      waves = waves.transpose() # transpose
      eneg,wfneg = [],[] # negative
      for (e,w) in zip(evals,waves): # loop
        if e<0: # negative
          eneg.append(e)
          wfneg.append(w)
      fo.write(str(x)+"     "+str(y)+"   ") # write k-point
      for op in operator: # loop over operators
          c = sum([braket_wAw(w,op) for w in wfneg]).real # expectation value
          fo.write(str(c)+"  ") # write in file
      fo.write("\n") # write in file
  fo.close() # close file  





def ev(h,operator=None,nk=30,**kwargs):
  """Calculate the expectation value of a certain number of operators"""
  from .densitymatrix import full_dm
  dm = full_dm(h,nk=nk,use_fortran=True,**kwargs)
  if operator is None: # no operator given on input
    operator = [] # empty list
  elif not isinstance(operator,list): # if it is not a list
    operator = [operator] # convert to list
  out = [(dm@op).trace() for op in operator] 
  out = np.array(out) # return the result
  out = out.reshape(out.shape[0]) # reshape in case there are indexes
  return out # return array






def total_energy(h,nk=10,nbands=None,use_kpm=False,random=False,
        kp=None,mode="mesh",tol=1e-1):
  """Return the total energy"""
  h.turn_dense()
  if h.is_sparse and not use_kpm: 
    print("Sparse Hamiltonian but no bands given, taking 20")
    nbands=20
  f = h.get_hk_gen() # get generator
  etot = 0.0 # initialize
  iv = 0
  def enek(k):
    """Compute energy in this kpoint"""
    hk = f(k)  # kdependent hamiltonian
    if use_kpm: # Kernel polynomial method
      return kpm.total_energy(hk,scale=10.,ntries=20,npol=100) # using KPM
    else: # conventional diagonalization
      if nbands is None: vv = lg.eigvalsh(hk) # diagonalize k hamiltonian
      else: 
          vv,aa = slg.eigsh(hk,k=4*nbands,which="LM",sigma=0.0) 
          vv = -np.sort(-(vv[vv<0.0])) # negative eigenvalues
          vv = vv[0:nbands] # get the negative eigenvlaues closest to EF
      return np.sum(vv[vv<0.0]) # sum energies below fermi energy
  # compute energy using different modes
  if mode=="mesh":
    from .klist import kmesh
    kp = kmesh(h.dimensionality,nk=nk)
    etot = np.mean(parallel.pcall(enek,kp)) # compute total eenrgy
  elif mode=="random":
    kp = [np.random.random(3) for i in range(nk)] # random points
    etot = np.mean(parallel.pcall(enek,kp)) # compute total eenrgy
  elif mode=="integrate":
    from scipy import integrate
    if h.dimensionality==1: # one dimensional
        etot = integrate.quad(enek,-1.,1.,epsabs=tol,epsrel=tol)[0]
    elif h.dimensionality==2: # two dimensional
        etot = integrate.dblquad(lambda x,y: enek([x,y]),-1.,1.,-1.,1.,
                epsabs=tol,epsrel=tol)[0]
    else: raise
  else: raise
  return etot






def eigenvalues(h0,nk=10):
    """Return all the eigenvalues of a Hamiltonian"""
    from . import klist
    h = h0.copy() # copy hamiltonian
    h.turn_dense()
    ks = klist.kmesh(h.dimensionality,nk=nk) # get grid
    hkgen = h.get_hk_gen() # get generator
    if parallel.cores==1:
      es = [] # empty list
      est = timing.Testimator(maxite=len(ks))
      for k in ks: # loop
        est.iterate()
        es += algebra.eigvalsh(hkgen(k)).tolist() # add
    else:
        f = lambda k: algebra.eigvalsh(hkgen(k)) # add
        es = parallel.pcall(f,ks) # call in parallel
        es = np.array(es)
        es = es.reshape(es.shape[0]*es.shape[1])
    return es # return all the eigenvalues







def reciprocal_map(h,f,nk=40,reciprocal=True,nsuper=1,filename="MAP.OUT"):
  """ Calculates the reciprocal map of something"""
  if reciprocal: R = h.geometry.get_k2K()
  else: R = np.matrix(np.identity(3))
  fo = open(filename,"w") # open file
  nt = nk*nk # total number of points
  ik = 0
  ks = [] # list with kpoints
  from . import parallel
  for x in np.linspace(-nsuper,nsuper,nk,endpoint=False):
    for y in np.linspace(-nsuper,nsuper,nk,endpoint=False):
        ks.append([x,y,0.])
  tr = timing.Testimator(filename.replace(".OUT",""),maxite=len(ks))
  def fp(ki): # function to compute the quantity
      if parallel.cores == 1: tr.iterate()
      else: print("Doing",ki)
      r = np.matrix(ki).T # real space vectors
      k = np.array((R*r).T)[0] # change of basis
      return f(k) # call function
  bs = parallel.pcall(fp,ks) # compute all the Berry curvatures
  for (b,k) in zip(bs,ks): # write everything
      fo.write(str(k[0])+"   "+str(k[1])+"     "+str(b.real))
      fo.write("     "+str(b.imag)+"\n")
      fo.flush()
  fo.close() # close file



def singlet_map(h,nk=40,nsuper=3,mode="abs"):
    """Compute a map with the superconducting singlet pairing"""
    hk = h.get_hk_gen() # get function
    from .superconductivity import extract_pairing
    def f(k): # define function
      m = hk(k) # call Hamiltonian
      (uu,dd,ud) = extract_pairing(m) # extract the pairing
#      return np.abs(ud) # trace
#      return np.sum(np.abs(ud)) # trace
      if mode=="trace": return ud.trace()[0,0] # trace
      elif mode=="det": return np.linalg.det(ud) # trace
      elif mode=="abs": return np.sum(np.abs(ud)) # trace
    reciprocal_map(h,f,nk=nk,nsuper=nsuper,filename="PAIRING_MAP.OUT")





def set_filling(h,filling=0.5,nk=10,extrae=0.,delta=1e-1):
    """Set the filling of a Hamiltonian"""
    if h.has_eh: raise
    fill = filling + extrae/h.intra.shape[0] # filling
    n = h.intra.shape[0]
    use_kpm = False
    if n>algebra.maxsize: # use the KPM method
        use_kpm = True
        print("Using KPM in set_filling")
    if use_kpm: # use KPM
        es,ds = h.get_dos(energies=np.linspace(-5.0,5.0,1000),
                use_kpm=True,delta=delta,nk=nk,random=False)
        from scipy.integrate import cumtrapz
        di = cumtrapz(ds,es)
        ei = (es[0:len(es)-1] + es[1:len(es)])/2.
        di /= di[len(di)-1] # normalize
        from scipy.interpolate import interp1d
        f = interp1d(di,ei) # interpolating function
        efermi = f(fill) # get the fermi energy
    else: # dense Hamiltonian, use ED
        es = eigenvalues(h,nk=nk)
        from .scftypes import get_fermi_energy
        efermi = get_fermi_energy(es,fill)
    h.shift_fermi(-efermi) # shift the fermi energy



def get_filling(h,**kwargs):
    """Get the filling of a Hamiltonian at this energy"""
    if h.check_mode("spinless_nambu"): # spinless Nambu Hamiltonian
        from .sctk import spinless
        return spinless.get_filling(h,**kwargs)
    elif h.check_mode("spinful_nambu"): raise # spinful Nambu
    else:
      es = spectrum.eigenvalues(self,**kwargs) # eigenvalues
      es = np.array(es)
      esf = es[es<0.0]
      return len(esf)/len(es) # return filling

