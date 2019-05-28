from __future__ import division
import numpy as np
import astropy
from scipy.stats import norm,beta,truncnorm
from mp_batman import run_batman
import pyluna
import pymultinest
import json
import matplotlib.pyplot as plt 
import os
import corner 
import emcee


"""
RpRstar = used for LUNA and batman
rhostar = used for LUNA and batman
bplan = used fomr LUNA and batman
q1 = used for LUNA and batman
q2 = used for LUNA and batman
rhoplan - used for LUNA and batman
sat_sma = used for LUNA ONLY -- REMOVE FROM BATMAN DICTIONARY!
sat_phase = used for LUNA only -- ""
sat_inc = used for LUNA only -- ""
sat_omega = used for LUNA only -- ""
MsatMP = used for LUNA only -- ""
RsatRp = used for LUNA only -- ""

### additional parameters that are used for batman but not LUNA!
Rstar = used for batman ONLY -- REMOVE FROM LUNA DICTIONARY!
long_peri = used for batman ONLY -- ""
ecc = used for batman ONLY -- ""

tau0 = used for LUNA and batman
Pplan = used for LUNA and batman

NPARAMS FOR LUNA = 14 
NPARAMS FOR BATMAN = 11

"""



### MULTINEST CUBE TRANSFORMATIONS
### note that in this context 'x' is the cube!
def transform_uniform(x,a,b):
    return a + (b-a)*x

def transform_loguniform(x,a,b):
    la=np.log(a)
    lb=np.log(b)
    return np.exp(la + x*(lb-la))

def transform_normal(x,mu,sigma):
    return norm.ppf(x,loc=mu,scale=sigma)

def transform_beta(x,a,b):
    return beta.ppf(x,a,b)

def transform_truncated_normal(x,mu,sigma,a=0.,b=1.):
    ar, br = (a - mu) / sigma, (b - mu) / sigma
    return truncnorm.ppf(x,ar,br,loc=mu,scale=sigma)


def pymn_prior(cube, ndim, nparams):
	### hopefully you can inherit these within the mp_multinest function!
	#for pidx, parprior, partuple in zip(np.arange(0,len(param_prior_forms),1), param_prior_forms, param_limit_tuple):

	for pidx, parlabs, parprior, partuple in zip(np.arange(0,len(mn_prior_forms),1), mn_param_labels, mn_prior_forms, mn_limit_tuple):
		if parprior == 'uniform':
			cube[pidx] = transform_uniform(cube[pidx], partuple[0], partuple[1])
		elif parprior == 'loguniform':
			cube[pidx] = transform_loguniform(cube[pidx], partuple[0], partuple[1])
		elif parprior == 'normal':
			cube[pidx] = transform_normal(cube[pidx], partuple[0], partuple[1])
		elif parprior == 'beta':
			cube[pidx] = transform_beta(cube[pidx], partuple[0], partuple[1])
		elif parprior == 'truncnorm':
			cube[pidx] = transform_truncated_normal(cube[pidx], partuple[0], partuple[1], partuple[2], partuple[3])



def emcee_lnprior(params):
	#LUNA_times, LUNA_fluxes = pyluna.run_LUNA(data_times, **param_dict, add_noise='n', show_plots='n')
	in_bounds = 'y'
	for param, parlim in zip(params, mn_limit_tuple):
		### test that they are in bounds
		if (param < parlim[0]) or (param > parlim[0]):
			in_bounds = 'n'
			break
	if in_bounds == 'n':
		return -np.inf 
	else:
		return 0.0 


def emcee_lnlike_LUNA(params, data_times, data_fluxes, data_errors):
	param_dict = {} ### initialize it

	for pidx, parlab in enumerate(mn_param_labels):
		param_dict[parlab] = params[pidx]

	LUNA_times, LUNA_fluxes = pyluna.run_LUNA(data_times, **param_dict, add_noise='n', show_plots='n')

	loglikelihood = np.nansum(-0.5 * ((LUNA_fluxes - data_fluxes) / data_errors)**2) ### SHOULD MAKE THIS BETTER, to super-penalize running out of bounds!
	return loglikelihood 


def emcee_lnlike_batman(params, data_times, data_fluxes, data_errors):
	param_dict = {} ### initialize it

	for pidx, parlab in enumerate(mn_param_labels):
		param_dict[parlab] = params[pidx]

	batman_times, batman_fluxes = run_batman(data_times, **param_dict, add_noise='n', show_plots='n')

	loglikelihood = np.nansum(-0.5 * ((batman_fluxes - data_fluxes) / data_errors)**2) ### SHOULD MAKE THIS BETTER, to super-penalize running out of bounds!
	return loglikelihood 


def emcee_lnprob_LUNA(params, data_times, data_fluxes, data_errors):
	lp = emcee_lnprior(params)
	if not np.isfinite(lp):
		return -np.inf 
	return lp + emcee_lnlike_LUNA(params, data_times, data_fluxes, data_errors)


def emcee_lnprob_batman(params, data_times, data_fluxes, data_errors):
	lp = emcee_lnprior(params)
	if not np.isfinite(lp):
		return -np.inf 
	return lp + emcee_lnlike_batman(params, data_times, data_fluxes, data_errors)




def pymn_loglike_LUNA(cube, ndim, nparams):
	### have to generate a model here, test it against the data, compute residuals, ultimately a log-likelihood
	### use a dictionary!
	### if run_LUNA takes (tau0, period, Rplan), for example, you can feed in a dictionary of values
	### with the keys equal to the keywords and it will interpret it! use run_LUNA(**dictionary)

	param_dict = {} ### initialize it

	for pidx, parlab in enumerate(mn_param_labels):
		param_dict[parlab] = cube[pidx]

	### now you should be able to run_LUNA(param_dict)
	LUNA_times, LUNA_fluxes = pyluna.run_LUNA(data_times, **param_dict, add_noise='n', show_plots='n')

	loglikelihood = np.nansum(-0.5 * ((LUNA_fluxes - data_fluxes) / data_errors)**2) ### SHOULD MAKE THIS BETTER, to super-penalize running out of bounds!
	return loglikelihood 



def pymn_loglike_batman(cube, ndim, nparams):
	### have to generate a model here, test it against the data, compute residuals, ultimately a log-likelihood
	### use a dictionary!
	### if run_LUNA takes (tau0, period, Rplan), for example, you can feed in a dictionary of values
	### with the keys equal to the keywords and it will interpret it! use run_LUNA(**dictionary)

	param_dict = {} ### initialize it

	for pidx, parlab in enumerate(mn_param_labels):
		param_dict[parlab] = cube[pidx]

	### now you should be able to run_LUNA(param_dict)
	batman_times, batman_fluxes = run_batman(data_times, **param_dict, add_noise='n', show_plots='n')

	loglikelihood = np.nansum(-0.5 * ((batman_fluxes - data_fluxes) / data_errors)**2) ### SHOULD MAKE THIS BETTER, to super-penalize running out of bounds!
	return loglikelihood 



def mp_multinest(times, fluxes, errors, param_labels, param_prior_forms, param_limit_tuple, nlive, targetID, modelcode="LUNA", show_plot='y'):
	### this function will start PyMultiNest!
	"""
	- param_labels is just an array of labels of the parameters you're fitting. MUST MATCH pyluna keywords! 
	- param_prior_forms is an array of prior formats, either 'uniform', 'loguniform', 'normal', 'beta', or 'truncnorm'.
	- param_limit_tuble is an array of tuples dictating the limits or shape parameters of the priors.
	"""

	global mn_param_labels
	global mn_prior_forms
	global mn_limit_tuple
	global data_times
	global data_fluxes
	global data_errors

	mn_param_labels = []
	mn_prior_forms = []
	mn_limit_tuple = []
	data_times = []
	data_fluxes = []
	data_errors = []

	for parlab, parprior, partup in zip(param_labels, param_prior_forms, param_limit_tuple):
		mn_param_labels.append(parlab)
		mn_prior_forms.append(parprior)
		mn_limit_tuple.append(partup)

	for t,f,e in zip(times, fluxes, errors):
		data_times.append(t)
		data_fluxes.append(f)
		data_errors.append(e)

	if os.path.exists('MultiNest_fits'):
		pass
	else:
		os.system('mkdir MultiNest_fits')


	if modelcode=='LUNA':
		outputdir = 'MultiNest_fits/LUNA/'+str(targetID)
	elif modelcode=='batman':
		outputdir = 'MultiNest_fits/batman/'+str(targetID)

	if os.path.exists(outputdir):
		pass
	else:
		os.system('mkdir '+outputdir)
		os.system('mkdir '+outputdir+'/chains')
	outputdir = outputdir+'/chains'

	if modelcode == 'LUNA':
		n_params = len(mn_param_labels)
		pymultinest.run(LogLikelihood=pymn_loglike_LUNA, Prior=pymn_prior, n_dims=n_params, n_live_points=nlive, outputfiles_basename=outputdir+'/'+str(targetID), resume=True, verbose=True)
	elif modelcode == "batman":
		n_params = len(mn_param_labels)
		pymultinest.run(LogLikelihood=pymn_loglike_batman, Prior=pymn_prior, n_dims=n_params, n_live_points=nlive, outputfiles_basename=outputdir+'/'+str(targetID), resume=True, verbose=True)
	
	json.dump(param_labels, open(outputdir+'/'+str(targetID)+"_params.json", 'w')) ### save parameter names

	"""
	if show_plot=='y':
		try:
			plot.figure()
			plt.plot(times, data, c='r', marker='+')
			a = pymultinest.Analyzer(outputfiles_basename=outputdir+'/'+str(targetID), n_params=len(param_labels))
			
			plot_dict = {}
			for parlab, dict_val in zip(param_labels, a.get_equal_weighted_posterior()[::100,:-1]):
				plot_dict[parlab] = dict_val

			plt.plot(data_times, run_LUNA(data_times, **plot_dict, add_noise='n'), c='b', alpha=0.3)
			plt.show()
		except:
			print("could not plot the solution.")
	"""

def mp_emcee(times, fluxes, errors, param_labels, param_prior_forms, param_limit_tuple, nwalkers, targetID, modelcode="LUNA", show_plot='y'):
	global mn_param_labels
	global mn_prior_forms
	global mn_limit_tuple
	global data_times
	global data_fluxes
	global data_errors

	mn_param_labels = []
	mn_prior_forms = []
	mn_limit_tuple = []
	data_times = []
	data_fluxes = []
	data_errors = []

	for parlab, parprior, partup in zip(param_labels, param_prior_forms, param_limit_tuple):
		mn_param_labels.append(parlab)
		mn_prior_forms.append(parprior)
		mn_limit_tuple.append(partup)

	for t,f,e in zip(times, fluxes, errors):
		data_times.append(t)
		data_fluxes.append(f)
		data_errors.append(e)

	if os.path.exists('emcee_fits'):
		pass
	else:
		os.system('mkdir emcee_fits')

	if os.path.exists('emcee_fits/LUNA'):
		pass
	else:
		os.system('mkdir emcee_fits/LUNA')

	if os.path.exists('emcee_fits/batman'):
		pass
	else:
		os.system('mkdir emcee_fits/batman')

	if modelcode=='LUNA':
		outputdir = 'emcee_fits/LUNA/'+str(targetID)
	elif modelcode=='batman':
		outputdir = 'emcee_fits/batman/'+str(targetID)

	if os.path.exists(outputdir):
		pass
	else:
		os.system('mkdir '+outputdir)
		os.system('mkdir '+outputdir+'/chains')
	outputdir = outputdir+'/chains'


	### INITIALIZE EMCEE PARAMETERS
	ndim = len(mn_param_labels)
	#pos = [result["x"] + 1e-4*np.random.randn(ndim) for i in range(nwalkers)]
	### pos is a list of arrays!
	pos =[]
	for walker in np.arange(0,nwalkers,1):
		walker_pos = []
		for partup in mn_limit_tuple:
			#print("partup[0], partup[1] = ", partup[0], partup[1])
			if (partup[0] != 0) and (partup[1] != 1) and (partup[1] - partup[0] > 1):
				if partup[1] - partup[0] > 1e3: ### implies a large range of values!
					parspot = np.random.choice(np.logspace(start=np.log10(partup[0]), stop=np.log10(partup[1]), num=1e4))
				else:
					parspot = np.random.randint(low=partup[0], high=partup[1]) + np.random.random()
			else:
				parspot = np.random.random()
			walker_pos.append(parspot)
		walker_pos = np.array(walker_pos)
		pos.append(walker_pos)

	if modelcode == 'LUNA':
		sampler = emcee.EnsembleSampler(nwalkers, ndim, emcee_lnprob_LUNA, args=(data_times, data_fluxes, data_errors))

	elif modelcode == "batman":
		sampler = emcee.EnsembleSampler(nwalkers, ndim, emcee_lnprob_batman, args=(data_times, data_fluxes, data_errors))

	### run the sampler 
	sampler.run_mcmc(pos, 10000)

	samples = sampler.chain[:,100:,:].reshape((-1, ndim))

	if show_plot == 'y':
		fig = corner.corner(samples, labels=mn_param_labels)
		plt.savefig(outputdir+'/'+str(targetID)+"_corner.png")



