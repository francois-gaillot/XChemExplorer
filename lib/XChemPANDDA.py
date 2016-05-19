import os, sys, glob
from datetime import datetime
from PyQt4 import QtGui, QtCore
from XChemUtils import mtztools
import XChemDB
import csv

class run_pandda_export(QtCore.QThread):

    def __init__(self,panddas_directory,datasource,initial_model_directory):
        QtCore.QThread.__init__(self)
        self.panddas_directory=panddas_directory
        self.datasource=datasource
        self.initial_model_directory=initial_model_directory
        self.db=XChemDB.data_source(self.datasource)
        self.db.create_missing_columns()
        self.db_list=self.db.get_empty_db_dict()

    def run(self):
        self.export_models()
        self.import_samples_into_datasouce()

    def import_samples_into_datasouce(self):

        db_dict=self.get_db_dict()

        progress_step=1
        if len(db_dict) != 0:
            progress_step=100/float(len(db_dict))
        else:
            progress_step=0
        progress=0

        self.emit(QtCore.SIGNAL('update_progress_bar'), progress)

        for xtal in db_dict:
#            print '==> XCE: updating panddaTable of data source with PANDDA site information for',xtal
            self.emit(QtCore.SIGNAL('update_status_bar(QString)'), 'updating data source with PANDDA site information for '+xtal)
            self.db.update_insert_panddaTable(xtal,db_dict[xtal])
            self.db.execute_statement("update mainTable set RefinementOutcome = '2 - PANDDA model' where CrystalName is '%s' and RefinementOutcome is null or RefinementOutcome is '1 - Analysis Pending'" %xtal)
            progress += progress_step
            self.emit(QtCore.SIGNAL('update_progress_bar'), progress)



    def get_db_dict(self):


        site_list = []

        with open(os.path.join(self.panddas_directory,'analyses','pandda_inspect_sites.csv'),'rb') as csv_import:
            csv_dict = csv.DictReader(csv_import)
            for i,line in enumerate(csv_dict):
                site_index=line['site_idx']
                name=line['Name']
                comment=line['Comment']
                site_list.append([site_index,name,comment])

        sample_dict={}

        with open(os.path.join(self.panddas_directory,'analyses','pandda_inspect_events.csv'),'rb') as csv_import:
            csv_dict = csv.DictReader(csv_import)
            for i,line in enumerate(csv_dict):
                db_dict={}
                sampleID=line['dtag']
                site_index=line['site_idx']
                event_index=line['event_idx']

                for entry in site_list:
                    if entry[0]==site_index:
                        site_name=entry[1]
                        site_comment=entry[2]
                        break

                # check if EVENT map exists in project directory
                event_map='event_map'
                for file in glob.glob(os.path.join(self.initial_model_directory,sampleID,'*ccp4')):
                    print file
                    filename=file[file.rfind('/')+1:]
                    if filename.startswith(sampleID+'-event_'+event_index) and filename.endswith('map.native.ccp4'):
                        event_map=file
                        break

                # initial pandda model and mtz file
                pandda_model='pandda_model'
                for file in glob.glob(os.path.join(self.initial_model_directory,sampleID,'*pdb')):
                    filename=file[file.rfind('/')+1:]
                    if filename.endswith('pandda-model.pdb'):
                        pandda_model=file
                        break
                inital_mtz='initial_mtz'
                for file in glob.glob(os.path.join(self.initial_model_directory,sampleID,'*mtz')):
                    filename=file[file.rfind('/')+1:]
                    if filename.endswith('pandda-input.mtz'):
                        inital_mtz=file
                        break

                db_dict['CrystalName']                  =   sampleID
                db_dict['PANDDApath']                   =   self.panddas_directory
                db_dict['PANDDA_site_index']            =   site_index
                db_dict['PANDDA_site_name']             =   site_name
                db_dict['PANDDA_site_comment']          =   site_comment
                db_dict['PANDDA_site_event_index']      =   event_index
                db_dict['PANDDA_site_event_comment']    =   line['Comment']
                db_dict['PANDDA_site_confidence']       =   line['Ligand Confidence']
                db_dict['PANDDA_site_ligand_placed']    =   line['Ligand Placed']
                db_dict['PANDDA_site_viewed']           =   line['Viewed']
                db_dict['PANDDA_site_interesting']      =   line['Interesting']
                db_dict['PANDDA_site_z_peak']           =   line['z_peak']
                db_dict['PANDDA_site_x']                =   line['x']
                db_dict['PANDDA_site_y']                =   line['y']
                db_dict['PANDDA_site_z']                =   line['z']
                db_dict['PANDDA_site_ligand_id']        =   'LIG'
                db_dict['PANDDA_site_event_map']        =   event_map
                db_dict['PANDDA_site_initial_model']    =   pandda_model
                db_dict['PANDDA_site_initial_mtz']      =   inital_mtz
                db_dict['PANDDA_site_spider_plot']      =   ''

                sample_dict[sampleID]=db_dict

        return sample_dict


    def export_models(self):
        Cmds = (
                'source '+os.path.join(os.getenv('XChemExplorer_DIR'),'setup-scripts','pandda.setup-sh')+'\n'
                '\n'
                'pandda.export'
                ' pandda_dir=%s' %self.panddas_directory+
                ' export_dir=%s' %self.initial_model_directory+
                ' export_ligands=False'
                ' generate_occupancy_groupings=True\n'
                )
        self.emit(QtCore.SIGNAL('update_status_bar(QString)'), 'running pandda.export: check terminal for details')
        os.system(Cmds)




class run_pandda_analyse(QtCore.QThread):

    def __init__(self,pandda_params):
        QtCore.QThread.__init__(self)
        self.data_directory=pandda_params['data_dir']
        self.panddas_directory=pandda_params['out_dir']
        self.submit_mode=pandda_params['submit_mode']
        if self.submit_mode == 'local machine':
            self.nproc=pandda_params['nproc']
        else:
            self.nproc='7'
        self.min_build_datasets=pandda_params['min_build_datasets']
        self.pdb_style=pandda_params['pdb_style']
        self.mtz_style=pandda_params['mtz_style']

    def run(self):
        if os.path.isfile(os.path.join(self.panddas_directory,'pandda.running')):
            return None
        else:
            if os.getenv('SHELL') == '/bin/tcsh' or os.getenv('SHELL') == '/bin/csh':
                source_file=os.path.join(os.getenv('XChemExplorer_DIR'),'setup-scripts','pandda.setup-csh')
            elif os.getenv('SHELL') == '/bin/bash':
                source_file=os.path.join(os.getenv('XChemExplorer_DIR'),'setup-scripts','pandda.setup-sh')
            else:
                source_file=''

            os.chdir(self.panddas_directory)
            Cmds = (
                '#!'+os.getenv('SHELL')+'\n'
                '\n'
                'source '+source_file+'\n'
                '\n'
                'cd '+self.panddas_directory+'\n'
                '\n'
                'pandda.analyse '
                ' data_dirs="'+self.data_directory+'"'
                ' out_dir='+self.panddas_directory+
                ' min_build_datasets='+self.min_build_datasets+
                ' maps.ampl_label=FWT maps.phas_label=PHWT'
                ' cpus='+self.nproc+
                ' pdb_style='+self.pdb_style+
                ' mtz_style='+self.mtz_style+'\n'
                )
            print Cmds

            f = open('pandda.sh','w')
            f.write(Cmds)
            f.close()
            if self.submit_mode=='local machine':
                print '==> running PANDDA on local machine'
                os.system('chmod +x pandda.sh')
                os.system('./pandda.sh &')
            else:
                print '==> running PANDDA on cluster, using qsub...'
                os.system('qsub pandda.sh')

class check_if_pandda_can_run:

    # reasons why pandda cannot be run
    # - there is currently a job running in the pandda directory
    # - min datasets available is too low
    # - required input paramters are not complete
    # - map amplitude and phase labels don't exist

    def __init__(self,pandda_params):
        self.data_directory=pandda_params['data_dir']
        self.panddas_directory=pandda_params['out_dir']
        self.min_build_datasets=pandda_params['min_build_datasets']
        self.pdb_style=pandda_params['pdb_style']
        self.mtz_style=pandda_params['mtz_style']

        self.problem_found=False
        self.error_code=-1

    def analyse_pdb_style(self):
        pdb_found=False
        for file in glob.glob(os.path.join(self.data_directory,self.pdb_style)):
            if os.path.isfile(file):
                pdb_found=True
                break
        if not pdb_found:
            self.error_code=1
            message=self.warning_messages()
        return message

    def analyse_mtz_style(self):
        mtz_found=False
        for file in glob.glob(os.path.join(self.data_directory,self.mtz_style)):
            if os.path.isfile(file):
                mtz_found=True
                break
        if not mtz_found:
            self.error_code=2
            message=self.warning_messages()
        return message

    def analyse_min_build_dataset(self):
        counter=0
        for file in glob.glob(os.path.join(self.data_directory,self.mtz_style)):
            if os.path.isfile(file):
                counter+=1
        if counter <= self.min_build_datasets:
            self.error_code=3
            message=self.warning_messages()
        return message

#    def analyse_amplitude_and_phase_labels(self):


#    def analyse_all_input_parameter(self):
#        print 'hallo'

    def warning_messages(self):
        message=''
        if self.error_code==1:
            message='PDB file does not exist'
        if self.error_code==2:
            message='MTZ file does not exist'
        if self.error_code==3:
            message='Not enough datasets available'

        return message