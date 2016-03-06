'''

Module for calculating power spectrum P(K) of 
halo/galaxy catalogs

'''
import os
import subprocess
import numpy as np

class Fcode: 
    def __init__(self, type, call_dict): 
        ''' Class that describes FORTRAN code for powerspectrum calculations 

        Parameters
        ----------
        type : (string)
            Type that specifies which fortran code class to get 

        call_dict : (dictionary)
            Dictionary that specifies the call sequence. 
        '''
        self.type = type    # FFT plk  pkmu
        self.call_dict = call_dict
        # fortran code directory 
        fcode_dir = '/home/users/hahn/projects/mock_betterizer/fortran/'

        if type == 'fft':                   # fft code
            f_name = 'zmapFFTil4_aniso_gen.f'
        elif type == 'plk':                 # P(k) code
            f_name = 'power3s_aniso.f'
        else: 
            raise NotImplementedError
        
        f_code = ''.join([fcode_dir, f_name])
        self.code = f_code
        self.exe = None 

    def fexe(self): 
        ''' Fortran executable that corresponds to fortran code. String parses 
        the shit out of the fortran code string to make it into a .exe 
        '''
        code_dir = ''.join(['/'.join((self.code).split('/')[:-1]), '/'])
        code_file = (self.code).split('/')[-1]
    
        fort_exe = ''.join([code_dir, 'exe/', '.'.join(code_file.rsplit('.')[:-1]), '.exe'])
        self.exe = fort_exe 
        return fort_exe 

    def Run(self):  
        code_t_mod, exe_t_mod = self._ModTime()
        if exe_t_mod <= code_t_mod: 
            self.Compile()
        cmdcall = self.CommandlineCall()
        subprocess.call(cmdcall.split())

    def Compile(self):
        ''' Compile fortran code
        '''
        fort_exe = self.fexe() 

        # compile command for fortran code. Quadruple codes have more
        # complex compile commands specified by Roman 
        if self.type == 'fft': 
            compile_cmd = ' '.join([ 
                'ifort -fast -o ', 
                fort_exe, 
                self.code, 
                '-L/usr/local/fftw3_intel_s/lib/ -lfftw3f'
                ])

                #' -L/usr/local/fftw_intel_s/lib -lsrfftw -lsfftw'

        elif self.type == 'plk': 
            compile_cmd = ' '.join([
                'ifort -fast -o', 
                fort_exe, 
                self.code
                ])
        else: 
            raise NotImplementedError()

        print ' ' 
        print 'Compiling -----'
        print compile_cmd
        print '----------------'
        print ' ' 

        # call compile command 
        subprocess.call(compile_cmd.split())

        return None 

    def CommandlineCall(self): 
        ''' Command line call for Fortran code
        '''
        # modification times of the fortran and executable files 
        fcode_t_mod, fexe_t_mod = self._ModTime()       
        if fcode_t_mod < fcode_t_mod: 
            raise ValueError("Compile failed")

        fort_exe = self.fexe() 

        if self.type == 'fft': 
            cmdline_call = ' '.join([
                self.exe, 
                str(0), 
                str(self.call_dict['Lbox']), 
                self.call_dict['input_file'], 
                self.call_dict['output_file'], 
                str(self.call_dict['i_obs']), 
                str(self.call_dict['redshift']),
                str(self.call_dict['OmegaM']), 
                str(self.call_dict['Ngrid'])
                ])

        elif self.type == 'plk': 
            cmdline_call = ' '.join([
                self.exe, 
                self.call_dict['fft_file'], 
                self.call_dict['output_file'], 
                str(self.call_dict['Nbin']), 
                str(self.call_dict['i_obs'])
                ])

        else: 
            raise NotImplementError()

        return cmdline_call

    def _ModTime(self): 
        ''' Modification time of fortran code and executable 
        '''
        if self.exe == None:    # if executable doesn't exist 
            self.fexe()
        # check if code exists
        if not os.path.isfile(self.code):   
            raise ValueError('No code file')
        else: 
            fcode_t_mod = os.path.getmtime(self.code)
        # check if executable exists 
        if not os.path.isfile(self.exe): 
            fexe_t_mod = 0 
        else: 
            fexe_t_mod = os.path.getmtime(self.exe)
        
        return [fcode_t_mod, fexe_t_mod]


class PofK(object): 
    def __init__(self, mock_file, space='real', obs_axis=None, Lbox=2500, 
            Ngrid=960, Nbin=480, z=0.562, OmegaM=0.31, pktype='plk'):
        ''' Class for calculating the power spectrum given galaxy/halo file.

        e.g. default set up 
            PofK(
                'test.dat', 
                space='real',       # redshift/real space
                obs_axis=None,      # observer's axis None, 'x', 'y', 'z'
                Lbox=2500,          # Lbox 
                Ngrid=960,          # Ngrid
                Nbin=480,           # Nbin 
                z=0.562,            # redshift 
                OmegaM=0.31         # Omega matter
                )
        '''
        self.input_file = mock_file 
        self.space = space 
        self.obs_axis = obs_axis
        self.Lbox = Lbox
        self.Ngrid = Ngrid
        self.Nbin = Nbin
        self.redshift = z
        self.OmegaM = OmegaM
        self.pktype = pktype

        self._CheckMock()       # check mock file
        self._ObsAxis()         # check obs axis
        self._MockContent()     # check mock content

        fft_file = self._FFTfile()  # FFT file
        pk_file = self._Pkfile()  # FFT file

        fftcall_dict = {
                'Lbox': self.Lbox, 
                'input_file': mock_file, 
                'output_file': fft_file, 
                'i_obs': self.i_obs, 
                'redshift': self.redshift, 
                'OmegaM': self.OmegaM, 
                'Ngrid': self.Ngrid
                }
        fftcode = Fcode('fft', fftcall_dict)
        #print fftcode.CommandlineCall()
        fftcode.Run()

        pkcall_dict = { 
                'fft_file': fft_file, 
                'output_file': pk_file, 
                'Nbin': self.Nbin, 
                'i_obs': self.i_obs
                }
        pkcode = Fcode(self.pktype, pkcall_dict) 
        #print pkcode.CommandlineCall()
        pkcode.Run()

    
    def _FFTfile(self):
        ''' FFT file of the mock catalog
        '''
        fft_dir = '/mount/riachuelo1/hahn/mock_betterizer/'
        nodir_file = self.input_file.rsplit('/')[-1]

        return ''.join([fft_dir, 'FFT', str(self.Ngrid), self.obs_str, '_', nodir_file])
    
    def _Pkfile(self):
        ''' Power Spectrum file of the mock catalog
        '''
        fft_dir = '/mount/riachuelo1/hahn/mock_betterizer/'
        nodir_file = self.input_file.rsplit('/')[-1]
        if self.pktype == 'plk': 
            pk_str = "Plk"
        elif self.pktype == 'pkmu': 
            pk_str = "Pkmu"

        return ''.join([fft_dir, pk_str, str(self.Ngrid), self.obs_str, '_', nodir_file])

    def _CheckMock(self): 
        ''' Check whether 
        '''
        # make sure run choices make sense
        if not os.path.isfile(self.input_file): 
            errmsg = ''.join([
                'Input file (', self.input_file, ') does not exist.', '\n'
                'Check the file name.'
                ])
            raise ValueError(errmsg)
        return None

    def _ObsAxis(self):
        ''' Check observer axis 
        '''
        if self.space == 'real':     # calculate P(k) in real space
            if self.obs_axis is not None: 
                obserrmsg = ''.join([
                    "You've selected that you want to calculate P(k) in Real Space.", "\n", 
                    "obs_axis has to be None if you want to calculate in Real Space"
                    ])
                raise ValueError(obserrmsg) 
            self.i_obs = 0  

        elif self.space == 'redshift': 
            # observer axis
            if self.obs_axis == 'x': 
                self.i_obs = 1
            elif obs_axis == 'y': 
                self.i_obs = 2
            elif obs_axis == 'z': 
                self.i_obs = 3
        else: 
            raise ValueError('space can only be real or redshift') 
        
        if self.i_obs == 0: 
            self.obs_str = 'real' 
        else: 
            self.obs_str = self.obs_axis+'OmegaM'+str(self.OmegaM)

        return None

    def _MockContent(self): 
        '''
        '''
        # Read first line of file to make sure that specified parameters 
        # makes sense. 
        f = open(self.input_file)  
        firstline = f.readline()
        if firstline[0] == '#': 
            cmterr = ''.join(['Input file has comments in the beginning.', '\n', 
                "The fortran code does not like comments in the beginning", 
                " and I don't want to fix it"])
            raise ValueError(cmterr)

        firstdata = [float(x) for x in firstline.split()]
        if len(firstdata) < 6 and i_obs > 0: 
            raise ValueError(
                    "Can't have redshift space distortions if data does not have velocities")

        return None




if __name__=='__main__':
    blah = PofK("/home/users/mv1003/catalog/PT_WNz0.562.dat", space='real', obs_axis=None, Lbox=2500, Ngrid=960, Nbin=480)
