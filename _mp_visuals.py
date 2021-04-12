from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
import os
#import astropy
import warnings
from astropy.io import ascii
from astropy.time import Time
import time
#import datetime
import pandas
import traceback
from astroquery.simbad import Simbad 
from astropy.constants import G, c, M_earth, M_jup, M_sun, R_earth, R_jup, R_sun, au 
from astropy.timeseries import LombScargle
import socket 

#### BELOW ARE MOONPY PACKAGES
from mp_tools import *
from mp_lcfind import *
from mp_detrend import untrendy_detrend, cofiam_detrend, george_detrend, medfilt_detrend, polyAM_detrend
from mp_batman import run_batman
from mp_fit import mp_multinest, mp_emcee
from mp_plotter import *
from cofiam import max_order
#from pyluna import run_LUNA, prepare_files
from pyluna import prepare_files
from mp_tpf_examiner import *
from scipy.interpolate import interp1d 


plt.rcParams["font.family"] = 'serif'

moonpydir = os.path.realpath(__file__)
moonpydir = moonpydir[:moonpydir.find('/_mp_visuals.py')]



def plot_lc(self, facecolor='LightCoral', edgecolor='k', errorbar='n', quarters='all', folded='n', include_flagged='n', detrended='y', show_errors='n', show_neighbors='n', time_format='native', pltshow='y', phase_offset=0.0, binned='n'):
	### THIS FUNCTION PLOTS THE LIGHT CURVE OBJECT.
	try:
		plot_times, plot_fluxes, plot_errors, plot_fluxes_detrend, plot_errors_detrend, plot_flags, plot_quarters = self.times, self.fluxes, self.errors, self.fluxes_detrend, self.errors_detrend, self.flags, self.quarters

	except:
		print("WARNING: light curve has not been detrended yet!")
		detrended = 'n'
		plot_times, plot_fluxes, plot_errors, plot_fluxes_detrend, plot_errors_detrend, plot_flags, plot_quarters = self.times, self.fluxes, self.errors, self.fluxes, self.errors, self.flags, self.quarters		


	### first step is to stitch the light curve together
	if type(quarters) != type('all'):
		### means you want only selected quarters, which should be in an array!
		qstokeep_idxs = []
		for quarter in quarters:
			if quarter in self.quarters:
				qstokeep_idxs.append(np.where(quarter == self.quarters)[0][0])
		qstokeep_idxs = np.array(qstokeep_idxs)

		plot_times, plot_fluxes, plot_errors, plot_fluxes_detrend, plot_errors_detrend, plot_flags, plot_quarters = plot_times[qstokeep_idxs], plot_fluxes[qstokeep_idxs], plot_errors[qstokeep_idxs], plot_fluxes_detrend[qstokeep_idxs], plot_errors_detrend[qstokeep_idxs], plot_flags[qstokeep_idxs], plot_quarters[qstokeep_idxs]

	if detrended == 'y':
		stitched_times, stitched_fluxes, stitched_errors, stitched_flags, stitched_quarters = np.hstack((plot_times)), np.hstack((plot_fluxes_detrend)), np.hstack((plot_errors_detrend)), np.hstack((plot_flags)), np.hstack((plot_quarters))
	else:
		stitched_times, stitched_fluxes, stitched_errors, stitched_flags, stitched_quarters = np.hstack((plot_times)), np.hstack((plot_fluxes)), np.hstack((plot_errors)), np.hstack((plot_flags)), np.hstack((plot_quarters))			

	if include_flagged=='n':
		### remove all data points with qflag != 0
		badflag_idxs = np.where(stitched_flags != 0)[0]
		stitched_times, stitched_fluxes, stitched_errors, stitched_flags = np.delete(stitched_times, badflag_idxs), np.delete(stitched_fluxes, badflag_idxs), np.delete(stitched_errors, badflag_idxs), np.delete(stitched_flags, badflag_idxs)
		assert np.all(stitched_flags == 0)


	if folded == 'n':
		if time_format == 'native':
			plot_stitched_times = stitched_times
		elif time_format == 'bjd':
			if self.telescope == 'kepler':
				plot_stitched_times = stitched_times + 2454833
			elif self.telescope == 'tess':
				plot_stitched_times = stitched_times + 2457000

		plt.scatter(plot_stitched_times, stitched_fluxes, facecolors=facecolor, edgecolors=edgecolor, s=10, zorder=1)
		if show_errors == 'y':
			plt.errorbar(plot_stitched_times, stitched_fluxes, yerr=stitched_errors, ecolor='k', zorder=0, alpha=0.5, fmt='none')

		if show_neighbors == 'y':
			### this will highlight all the other transits for the neighbors (if any)
			neighbors = self.neighbor_dict.keys()

			for neighbor in neighbors:
				neighbor_taus = self.neighbor_dict[neighbor].taus 
				neighbor_dur = self.neighbor_dict[neighbor].duration_days 

				neighbor_transit_idxs = []
				for nt in neighbor_taus:
					ntidxs = np.where((stitched_times >= (nt - 0.5*neighbor_dur)) & (stitched_times <= (nt + 0.5*neighbor_dur)))[0]
					neighbor_transit_idxs.append(ntidxs)
				neighbor_transit_idxs = np.hstack(neighbor_transit_idxs)
				#plt.scatter(stitched_times[neighbor_transit_idxs], stitched_fluxes[neighbor_transit_idxs], facecolors='g', s=10, marker='x')
				plt.scatter(plot_stitched_times[neighbor_transit_idxs], stitched_fluxes[neighbor_transit_idxs], s=10, marker='x', label=neighbor)
		

			### PLOT THE TARGET TRANSITS TOO!
			target_taus = self.taus 
			target_dur = self.duration_days
			target_transit_idxs = []
			for tt in target_taus:
				ttidxs = np.where((stitched_times >= (tt - 0.5*target_dur)) & (stitched_times <= (tt + 0.5*target_dur)))[0]
				target_transit_idxs.append(ttidxs)
			target_transit_idxs = np.hstack(target_transit_idxs)
			plt.scatter(plot_stitched_times[target_transit_idxs], stitched_fluxes[target_transit_idxs], s=10, marker='x', color='Indigo', label='target')

		plt.legend()					


	elif folded == 'y':
		try:
			self.fold(detrended=detrended, phase_offset=phase_offset)
		except:
			self.get_properties(locate_neighbor='n')
			self.fold(phase_offset=phase_offset)


		if binned == 'n':	
			plt.scatter(self.fold_times, self.fold_fluxes, facecolors=facecolor, edgecolors=edgecolor, s=10, zorder=1)
			if show_errors == 'y':
				plt.errorbar(self.fold_times, self.fold_fluxes, yerr=self.fold_errors, ecolor='k', zorder=0, alpha=0.5, fmt='none')

		elif binned == 'y':
			fold_bin_step = 0.0005
			fold_bins = np.arange(np.nanmin(self.fold_times), np.nanmax(self.fold_times), fold_bin_step)
			fold_bin_fluxes = []
			fold_bin_errors = []
			for fb in fold_bins:
				fb_idxs = np.where((self.fold_times >= fb- fold_bin_step/2) & (self.fold_times < fb + fold_bin_step/2))[0]
				fold_bin_fluxes.append(np.nanmedian(self.fold_fluxes[fb_idxs]))
				fold_bin_errors.append(np.nanstd(self.fold_fluxes[fb_idxs])/np.sqrt(len(fb_idxs)))

			fold_bin_fluxes, fold_bin_errors = np.array(fold_bin_fluxes), np.array(fold_bin_errors)

			plt.scatter(self.fold_times, self.fold_fluxes, facecolors='k', s=5, zorder=0, alpha=0.2)
			plt.scatter(fold_bins, fold_bin_fluxes, facecolor=facecolor, alpha=0.7, s=15, zorder=1)
			#plt.errorbar(fold_bins, fold_bin_fluxes, yerr=fold_bin_errors, ecolor='k', zorder=0, fmt='none')


	#plt.xlabel('BKJD')
	if (self.telescope.lower() == 'kepler') or (self.telescope.lower() == 'k2'):
		if folded=='y':
			plt.xlabel('Phase')
		else:
			plt.xlabel('BKJD')
	elif (self.telescope.lower() == 'tess'):
		if folded=='y':
			plt.xlabel('Phase')
		else:
			plt.xlabel('BTJD')
	plt.ylabel('Flux')
	try:
		plt.title(str(self.target))
	except:
		pass

	if pltshow == 'y':	
		plt.show()
	else:
		pass



def plot_corner(self, fitter='emcee', modelcode='batman', burnin_pct=0.1):
	import corner

	### THIS FUNCTION GENERATES A CORNER PLOT BASED ON YOUR MODEL FITS.
	if fitter == 'multinest':
		### use this to generate a corner plot from the fit results.
		fit_resultsdir = moonpydir+'/MultiNest_fits/'+str(self.target)+'/chains'
		PEWfile = np.genfromtxt(fit_resultsdir+'/'+str(self.target)+'post_equal_weights.dat')

		json_file = open(fit_resultsdir+'/'+str(self.target)+'_params.json', mode='r')
		json_params = json_file.readline()
		json_params = json_params.split(',')

		PEWdict = {}
		for njpar, jpar in enumerate(json_params):
			while jpar.startswith(' '):
				jpar = jpar[1:]
			while jpar[-1] == ' ':
				jpar = jpar[:-1]
			while jpar.startswith('"'):
				jpar = jpar[1:]
			while jpar[-1] == '"':
				jpar = jpar[:-1]
			PEWdict[jpar] = PEWfile.T[njpar]

		### as a test, just generate a simple histogram
		for param in PEWdict.keys():
			n, bins, edges = plt.hist(PEWdict[param], bins=50, facecolor='green', edgecolor='k', alpha=0.7)
			plt.title(param)
			plt.show()

	elif fitter == 'emcee':
		if modelcode=='batman':
			chainsdir = moonpydir+'/emcee_fits/batman/'+str(self.target)+'/chains'
		elif modelcode=='LUNA':
			chainsdir=moonpydir+'/emcee_fits/LUNA/'+str(self.target)+'/chains'
		samples = np.genfromtxt(chainsdir+'/'+str(self.target)+'_mcmc_chain.txt')
		sample_shape = samples.shape
		samples = samples[int(burnin_pct*sample_shape[0]):,1:]


	self.initialize_priors(modelcode=modelcode)
	fig = corner.corner(samples, labels=self.param_labels)
	plt.savefig(chainsdir+'/'+str(self.target)+"_corner.png")
	plt.close()





def plot_bestmodel(self, fitter, modelcode, folded=False, burnin_pct=0.1):
	### THIS FUNCTION PLOTS YOUR BEST FIT LIGHT CURVE MODEL OVER THE DATA.
	if folded == True:
		self.fold()

	if modelcode == "LUNA":
		folded = False ### should not be generating a folded light curve for a moon fit.

	self.initialize_priors(modelcode=modelcode)

	if fitter == 'emcee':
		if modelcode=='batman':
			chainsdir = moonpydir+'/emcee_fits/batman/'+str(self.target)+'/chains'
		elif modelcode=='LUNA':
			chainsdir=moonpydir+'/emcee_fits/LUNA/'+str(self.target)+'/chains'
		samples = np.genfromtxt(chainsdir+'/'+str(self.target)+'_mcmc_chain.txt')
		sample_shape = samples.shape
		samples = samples[int(burnin_pct*sample_shape[0]):,1:]

		### 
		best_fit_dict = {}
		for npar, parlab in enumerate(self.param_labels):
			best_fit_dict[parlab] = np.nanmedian(samples.T[npar])
		print("best fit values: ")
		for parkey in best_fit_dict.keys():
			print(parkey, ' = ', best_fit_dict[parkey])

		if modelcode == 'batman':
			### use batman to generate a model!!!
			if folded == True:
				batman_times, batman_fluxes = run_batman(self.fold_times, **best_fit_dict, add_noise='n', show_plots='n')
				plt.scatter(np.hstack(self.fold_times), np.hstack(self.fluxes_detrend), facecolor='LightCoral', edgecolor='k')
			else:
				batman_times, batman_fluxes = run_batman(self.times, **best_fit_dict, add_noise='n', show_plots='n')					
				plt.scatter(np.hstack(self.times), np.hstack(self.fluxes_detrend), facecolor='LightCoral', edgecolor='k')
			batman_sort = np.argsort(batman_times)
			batman_times, batman_fluxes = batman_times[batman_sort], batman_fluxes[batman_sort]
			plt.plot(batman_times, batman_fluxes, c='g', linewidth=2)
			plt.show()






def fold(self, detrended='y', phase_offset=0.0):
	### this method will phase fold your light curve. 
	### first tau in the time series:
	try:
		#first_tau = self.tau0
		first_tau = self.taus[0]
	except:
		self.get_properties()
		first_tau = self.taus[0]

	ftidx = 0
	while first_tau < np.nanmin(np.hstack(self.times)):
		ftidx += 1
		first_tau = self.taus[ftidx]

	fold_times = ((((np.hstack(self.times) - first_tau - 0.5*self.period - phase_offset*self.period) % self.period) / self.period)) ### yields the remainder!
	fold_times = fold_times - 0.5

	if detrended == 'y':
		fold_fluxes = np.hstack(self.fluxes_detrend)
		fold_errors = np.hstack(self.errors_detrend)
	else:
		fold_fluxes = np.hstack(self.fluxes)
		fold_errors = np.hstack(self.errors)

	self.fold_times = fold_times
	self.fold_fluxes = fold_fluxes
	self.fold_errors = fold_errors
	#self.fold_tau = fold_first_tau





def examine_TPF(self, quarters=None, time_lims=None, detrend='y', mask_idxs=None):
	if type(quarters) == type(None):
		quarters = self.quarters 
	tpf_examiner(self.target, quarters=quarters, Tdur=self.duration_days, time_lims=time_lims, detrend=detrend, mask_idxs=mask_idxs, find_alias='y')




def genLS(self, show_plot = 'y', compute_fap='n', LSquarters=None):
	### this function generates a Lomb-Scargle Periodogram!
	LSperiods = []
	LSmaxpower_periods = []
	LSpowers = []
	LSfaps = []
	nquarters = len(self.quarters)

	if type(LSquarters) == type(None):
		LSquarters = self.quarters

	#for qidx in np.arange(0,nquarters,1):
	for qidx in np.arange(0,nquarters,1):
		this_quarter = self.quarters[qidx]
		if this_quarter not in LSquarters: ### use this in case you've only specified select quarters.
			continue

		print("processing LS for ", this_quarter)
		if nquarters != 1:
			qtimes, qfluxes, qerrors = self.times[qidx], self.fluxes[qidx], self.errors[qidx]
		else:
			qtimes, qfluxes, qerrors = self.times, self.fluxes, self.errors 
		maxperiod = 0.5 * (np.nanmax(qtimes) - np.nanmin(qtimes))
		minperiod = 0.5
		minfreq, maxfreq = 1/maxperiod, 1/minperiod
		qls = LombScargle(qtimes, qfluxes, qerrors)
		qfreq, qpower = qls.autopower(minimum_frequency=minfreq, maximum_frequency=maxfreq)
		qperiods = 1/qfreq
		if compute_fap == 'y':
			qfap = qls.false_alarm_probability(qpower.max(), method='bootstrap')
			probabilities = [0.1, 0.05, 0.01]
			quarter_FALs = qls.false_alarm_level(probabilities)

		if show_plot == 'y':
			#try:
			random_color = np.random.rand(3)
			plt.plot(qperiods[::-1], qpower[::-1], c=random_color)
			if compute_fap == 'y':
				plt.plot(qperiods[::-1], np.linspace(quarter_FALs[1], quarter_FALs[1], len(qperiods[::-1])), c=random_color)
			#except:
			#	plt.plot(qperiods[::-1], qpower[::-1])
			#	if compute_fap == 'y':
			#		plt.plot(qperiods[::-1], np.linspace(quarter_FALs[1], quarter_FALs[1], len(qperiods[::-1])))

		LSperiods.append(qperiods)
		max_power_period = qperiods[np.nanargmax(qpower)]
		LSmaxpower_periods.append(max_power_period)
		LSpowers.append(qpower)
		if compute_fap == 'y':
			LSfaps.append(qfap)

	if show_plot == 'y':
		plt.xscale('log')
		#plt.xlim(np.nanmin(qperiods), np.nanmax(qperiods))
		plt.xlabel('Period [days]')
		plt.ylabel('Power')
		plt.title(self.target)
		plt.show()

	LSperiods, LSpowers, LSfaps = np.array(LSperiods), np.array(LSpowers), np.array(LSfaps)

	print('LS max power periods = ', LSmaxpower_periods)
	LSperiod_median = np.nanmedian(LSmaxpower_periods)
	LSperiod_std = np.nanstd(LSmaxpower_periods)
	print('median(LS max power periods) = ', LSperiod_median)
	print('std(LS max power periods) = ', LSperiod_std)

	self.LSperiods = LSperiods
	self.LSpowers = LSpowers 
	self.LSfaps = LSfaps
	self.LSmaxperiods = LSmaxpower_periods 












