"""
Functions related to the flux: Poynting vector, cross-sections, etc.
"""

import numpy as np
from scipy import constants
import miepy
from my_pytools.my_numpy.integrate import simps_2d

def particle_cross_sections(p_scat, q_scat, p_src, q_src, radius, k, n, mu, n_b, mu_b):
    """Compute the scattering, absorption, and extinction cross-sections for a particle
       
       Arguments:
           p_scat[rmax]    particel p coefficients
           q_scat[rmax]    particel q coefficients
           p_src[rmax]     source p coefficients at particle
           q_src[rmax]     source q coefficients at particle
           radius          particle radius
           k               wavenumber
           n               particle index of refraction
           mu              particle permeability
           n_b             background index of refraction
           mu_b            background permeability
    """
    Lmax = int(-1 + (1+len(p_scat))**0.5)

    Cext  = np.zeros([2, Lmax], dtype=float)
    Cabs  = np.zeros([2, Lmax], dtype=float)

    riccati = miepy.special_functions.riccati_1_single

    factor = 4*np.pi/k**2

    xj = k*radius
    mj = n/n_b
    yj = xj*mj

    for n in range(1,Lmax+1):
        for m in range(-n,n+1):
            r = n**2 + n - 1 + m

            # Cscat[0,n-1] += factor*np.abs(p_scat[r])**2
            # Cscat[1,n-1] += factor*np.abs(q_scat[r])**2

            psi_x, psi_xp = riccati(n, xj)
            psi_y, psi_yp = riccati(n, yj)
            
            Dn = -np.divide(np.real(1j*mj*mu_b*mu*psi_y*np.conj(psi_yp)),
                            np.abs(mu_b*mj*psi_y*psi_xp - mu*psi_x*psi_yp)**2)
            Cn = -np.divide(np.real(1j*np.conj(mj)*mu_b*mu*psi_y*np.conj(psi_yp)),
                            np.abs(mu*psi_y*psi_xp - mu_b*mj*psi_x*psi_yp)**2)

            Cabs[0,n-1] += Dn*factor*np.abs(p_scat[r])**2
            Cabs[1,n-1] += Cn*factor*np.abs(q_scat[r])**2

            #TODO should this be p_src or p_inc?
            Cext[0,n-1] += factor*np.real(np.conj(p_src[r])*p_scat[r])
            Cext[1,n-1] += factor*np.real(np.conj(q_src[r])*q_scat[r])

    Cscat = Cext - Cabs
    return Cscat, Cabs, Cext

def cluster_cross_sections(p_cluster, q_cluster, p_src, q_src, k):
    """Compute the scattering, absorption, and extinction cross-sections for a cluster
       
       Arguments:
           p_cluster[rmax]    cluster p coefficients
           q_cluster[rmax]    cluster q coefficients
           p_src[rmax]        source p coefficients at origin
           q_src[rmax]        source q coefficients at origin
           k                  wavenumber
    """
    Lmax = int(-1 + (1+len(p_cluster))**0.5)

    Cscat = np.zeros([2, Lmax], dtype=float)
    Cext  = np.zeros([2, Lmax], dtype=float)

    factor = 4*np.pi/k**2

    for n in range(1,Lmax+1):
        for m in range(-n,n+1):
            r = n**2 + n - 1 + m

            Cscat[0,n-1] += factor*np.abs(p_cluster[r])**2
            Cscat[1,n-1] += factor*np.abs(q_cluster[r])**2

            Cext[0,n-1] += factor*np.real(np.conj(p_src[r])*p_cluster[r])
            Cext[1,n-1] += factor*np.real(np.conj(q_src[r])*q_cluster[r])

    Cabs = Cext - Cscat
    return Cscat, Cabs, Cext

#TODO eps/mu role here (related to our definition of the H field, eps/mu factor)
#TODO factor of 1/2 for complex fields not present???
def poynting_vector(E, H, eps=1, mu=1):
    """Compute the Poynting vector
    
       Arguments:
           E[3,...]   electric field data
           H[3,...]   magnetic field data
           eps        medium permitvitty (default: 1)
           mu         medium permeability (default: 1)

       Returns S[3,...]
    """

    S = np.cross(E, np.conj(H), axis=0)
    n_b = np.sqrt(eps*mu)

    return np.real(S)/n_b

#TODO is this right, can it be more useful?
def flux_from_poynting(E, H, Ahat, eps=1, mu=1):
    """Compute the flux from the E and H field over some area using the Poynting vector

       Arguments:
           E[3,...]             electric field values on some surface
           H[3,...]             magnetic field values on some surface
           Ahat[3,...]          normal vectors of the surface
           eps                  medium permitvitty (default: 1)
           mu                   medium permeability (default: 1)

       Returns flux (scalar)
    """
    S = poynting_vector(E, H, eps, mu)
    integrand = np.einsum('i...,i...->...', S, Ahat)

    return np.sum(integrand)

def flux_from_poynting_sphere(E, H, radius, eps=1, mu=1):
    """Compute the flux from the E and H field on the surface of a sphere using the Poynting vector

       Arguments:
           E[3,Ntheta,Nphi]     electric field values on the surface of a sphere
           H[3,Ntheta,Nphi]     magnetic field values on the surface of a sphere
           radius               radius of sphere 
           eps                  medium permitvitty (default: 1)
           mu                   medium permeability (default: 1)

       Returns flux (scalar)
    """
    S = poynting_vector(E, H, eps, mu)

    Ntheta, Nphi = E.shape[1:]
    THETA, PHI = miepy.coordinates.sphere_mesh(Ntheta)
    rhat,*_ = miepy.coordinates.sph_basis_vectors(THETA, PHI)

    tau = np.linspace(-1, 1, Ntheta)
    phi = np.linspace(0, 2*np.pi, Nphi)
    dA = radius**2

    integrand = np.einsum('ixy,ixy->xy', S, rhat)*dA
    flux = simps_2d(tau, phi, integrand)

    return flux

def _gmt_cross_sections_from_poynting(gmt, radius, sampling=30):
    """FOR TESTING ONLY!
    Given GMT object and particle number i, return cross-sections (C,A,E) from poynting vector
    """
    X,Y,Z,THETA,PHI,tau,phi = miepy.coordinates.cart_sphere_mesh(radius, gmt.origin, sampling)

    E_tot = gmt.E_field(X, Y, Z)
    H_tot = gmt.H_field(X, Y, Z)

    E_scat = gmt.E_field(X, Y, Z, source=False)
    H_scat = gmt.H_field(X, Y, Z, source=False)

    eps_b = gmt.material_data.eps_b
    mu_b = gmt.material_data.mu_b
    C = flux_from_poynting_sphere(E_scat, H_scat, radius, eps_b, mu_b)
    A = -flux_from_poynting_sphere(E_tot, H_tot, radius, eps_b, mu_b)

    return C, A, C+A
