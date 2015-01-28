#
# Collective Mind
#
# See cM LICENSE.txt for licensing details.
# See cM Copyright.txt for copyright details.
#
# Developer(s): (C) Grigori Fursin, started on 2011.09
#

# Should always be here
ini={}
cm_kernel=None

# Local settings
import os
import sys
import time
import json
import copy

# ============================================================================
def init(i):
    return {'cm_return':0}

# ============================================================================
def change_work_dir(i):

    """
    Chaning working directory

    Input:  {
              (work_dir)                 - change to this working directory before running code
                  or
              (work_dir_repo_uoa)        - change to the working directory in the repository (repo UOA)
              (work_dir_module_uoa)      - change to the working directory in the repository (module UOA)
              (work_dir_data_uoa)        - change to the working directory in the repository (data UOA)
            }

    Output: {
              cm_return                 - if =0, success
              work_dir                  - selected working directory 
            }
    """

    # Changing to working directory
    sys.stdout.flush()
    work_dir=''
    if 'work_dir' in i: work_dir=i['work_dir']
    elif ('work_dir_module_uoa' in i and 'work_dir_data_uoa' in i):
       # Change path to another directory
       ii={'cm_run_module_uoa':i['work_dir_module_uoa'],
           'cm_action':'load',
           'cm_data_uoa':i['work_dir_data_uoa']}
       if 'work_dir_repo_uoa' in i: ii['cm_repo_uoa']=i['work_dir_repo_uoa']
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r
       work_dir=r['cm_path']

    if work_dir!='':
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Changing path to '+work_dir+' ...')
       os.chdir(work_dir)

    return {'cm_return':0, 'work_dir':work_dir}

# ============================================================================
def get_env(i):

    """
    cM web index

    Input:  {
              cm_data_uoa - code UOA to prepare environment script name
              os_uoa      - OS configuration to prepare extension
            }

    Output: {
              cm_return  - return code >0 if error
            }
    """

    if 'os_uoa' not in i or i['os_uoa']=='':
       return {'cm_return':1, 'cm_error': '"os_uoa" is not defined for "get_env" in "code" module'}

    # Load OS
    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['os'],
        'cm_action':'load',
        'cm_data_uoa':i['os_uoa']}
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    os_cfg=r['cm_data_obj']['cfg']

    # Prepare script
    s=ini['cfg']['cm_env_prefix']+i['cm_data_uoa']+os_cfg['script_ext']

    return {'cm_return':0, 'cm_string':s}

# ============================================================================
def run(i):

    """
    Run code (binary or script)

    Input:  {
              (run_host_os_uoa)          - host OS UOA (if not set, use default OS from kernel)
              (run_target_os_uoa)        - target OS UOA (if not set, use run_host_uoa_os)

              (run_target_processor_uoa) - target processor UOA (not strictly needed - can add some helper parameters before executing code)

              --------------------------------------------------------------------------------------------
              run_cmd_key                - if !='', set all further run parameters (including target name) 
                                           from the work_dir_data_uoa (must be set)
              (dataset_uoa)              - use dataset to update cmd params from above
                 or
              run_cmd                    - command line to run
                 or
              run_script                 - use the following script (add extension from run_target_os)
              run_script_uoa             - take script from this entry in os.script (add extension from run_target_os)
                 or
              (run_cmd1)                 - following format: run_cmd1 run_cmd_name|binary_name run_cmd2 run_cmd_main run_cmd3 > run_cmd_out1 2> run_cmd_out2
              (run_cmd_name)
              (run_cmd2)
              (run_cmd_main) or (binary_name)
              (run_cmd3)
              (run_cmd_out1)
              (run_cmd_out2)
              --------------------------------------------------------------------------------------------

              (work_dir)                 - change to this working directory before running code
                  or
              (work_dir_repo_uoa)        - change to the working directory in the repository (repo UOA)
              (work_dir_module_uoa)      - change to the working directory in the repository (module UOA)
              (work_dir_data_uoa)        - change to the working directory in the repository (data UOA)

              (run_input_files)          - list of files needed to run code (can be copied to the remote host system)
              (run_output_files)         - list of files that will be created (for validation, etc)

              (code_deps)                - list with code UOA for dependencies [{"index":"uoa"} ...]
              (skip_code_deps)           - if 'yes', skip code deps

              (run_set_env1)             - array with environment variables to be set before code deps
              (run_set_env2)             - array with environment variables to be set before executable

              (run_commands_before)      - run commands before executable
              (run_commands_after)       - run commands after executable

              (cm_dependencies)          - dependencies that set all other dependencies (code/include/lib).
                                           Format [{"class UOA":"code UOA"},{},...]

              (run_timeout)              - time out for run (overheads may occur)

              (keep_all_files)           - if 'yes', do not remove tmp files and do not clean up remote device
              (cm_verbose)               - if 'yes', print all info
            }

    Output: {
              cm_return          - return code = 0, if successful

              timed_out          - 'yes' if timed out
              failed_run         - 'yes' if return code !=0 or timed out or binary doesn't exist
              run_time_by_module - run time measured by module
              exit_code          - exit code of the system call
              run_cmd            - final run cmd
              work_dir           - work directory
              run_output_files   - final output files
            }
    """

    # Check verbose - yes, by default
    vrb=i.get('cm_verbose','yes')

    if vrb=='yes':
#       cm_kernel.print_for_con('***********************************************')
       cm_kernel.print_for_con('Running code ...')

    # Load OS configuration
    host_os_uoa=''
    if 'run_host_os_uoa' in i and i['run_host_os_uoa']!='': host_os_uoa=i['run_host_os_uoa']
    elif 'cm_default_os_uoa' in cm_kernel.ini['dcfg'] and cm_kernel.ini['dcfg']['cm_default_os_uoa']!='':
       host_os_uoa=cm_kernel.ini['dcfg']['cm_default_os_uoa']

    if host_os_uoa=='':
       return {'cm_return':1, 'cm_error':'"host_os_uoa" is not set and not in kernel'}

    target_os_uoa=''
    if 'run_target_os_uoa' in i and i['run_target_os_uoa']!='': target_os_uoa=i['run_target_os_uoa']
    elif host_os_uoa!='': target_os_uoa=host_os_uoa

    if vrb=='yes':
       sys.stdout.flush()
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Loading host os '+host_os_uoa+' ...')
    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['os'],
        'cm_action':'load',
        'cm_data_uoa':host_os_uoa}
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    host_os_cfg=r['cm_data_obj']['cfg']
    host_os_path=r['cm_path']
    host_os_uid=r['cm_uid']
    host_os_alias=r['cm_alias']

    if vrb=='yes':
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Loading target os '+target_os_uoa+' ...')
    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['os'],
        'cm_action':'load',
        'cm_data_uoa':target_os_uoa}
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    target_os_cfg=r['cm_data_obj']['cfg']
    target_os_path=r['cm_path']
    target_os_uid=r['cm_uid']
    target_os_alias=r['cm_alias']

    # Dependencies
    code_deps=i.get('code_deps',[])

    # Check if code_deps set additional parameters
    qq=i.get('cm_dependencies',{})
    if len(qq)>0:
       if vrb=='yes':
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Updating code dependencies from cm_dependencies ...')

       code_deps1=[]

       for q in i.get('cm_dependencies',{}):
           yy=q.keys()[0]
           x=q[yy]

           jj={'cm_run_module_uoa':ini['cfg']['cm_modules']['class'],
               'cm_data_uoa':yy,
               'cm_action':'load'}
           rj=cm_kernel.access(jj)
           if rj['cm_return']>0: return rj

           drj=rj['cm_data_obj']['cfg']

           vcd=drj.get('build_code_deps_var','')
           if vcd!='': code_deps1.append({vcd:x})

       for q in code_deps: code_deps1.append(q)

       code_deps=code_deps1

    i['code_deps']=code_deps

    processor_params={}
    if 'run_target_processor_uoa' in i and i['run_target_processor_uoa']!='':
       if vrb=='yes':
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Loading target processor '+i['run_target_processor_uoa']+' ...')
       ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['processor'],
           'cm_action':'load',
           'cm_data_uoa':i['run_target_processor_uoa']}
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r

       target_processor_cfg=r['cm_data_obj']['cfg']
       target_processor_path=r['cm_path']
       target_processor_uid=r['cm_uid']
       target_processor_alias=r['cm_alias']

       if 'family' in target_processor_cfg:
          processor_params['CM_PROCESSOR_FAMILY']=target_processor_cfg['family']
       if 'architecture' in target_processor_cfg:
          processor_params['CM_PROCESSOR_ARCH']=target_processor_cfg['architecture']
       if 'bits' in target_processor_cfg:
          processor_params['CM_PROCESSOR_BITS']=target_processor_cfg['bits']

    # Changing to working directory
    sys.stdout.flush()
    work_dir=''
    if 'work_dir' in i: work_dir=i['work_dir']
    elif ('work_dir_module_uoa' in i and 'work_dir_data_uoa' in i):
       # Change path to another directory
       ii={'cm_run_module_uoa':i['work_dir_module_uoa'],
           'cm_action':'load',
           'cm_data_uoa':i['work_dir_data_uoa']}
       if 'work_dir_repo_uoa' in i: ii['cm_repo_uoa']=i['work_dir_repo_uoa']
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r
       work_dir=r['cm_path']

    if work_dir!='':
       if vrb=='yes':
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Changing path to '+work_dir+' ...')
       os.chdir(work_dir)

    e1a={}

    # Check if remote
    remote=False
    if target_os_cfg.get('remote','')=='yes': 
       remote=True
       files=[]

    # Check vars
    run_input_files=i.get('run_input_files',[])

    run_name=''
    run_cmd=''

    if i.get('run_script','')!='':
       if vrb=='yes':
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Using script '+i['run_script'])

       r=prepare_sub_script({'run_script':i['run_script'],
                             'run_script_uoa':i.get('run_script_uoa',''),
                             'target_os_cfg':target_os_cfg,
                             'run_cmd':i.get('run_cmd',''),
                             'run_cmd_out1':i.get('run_cmd_out1',''),
                             'run_cmd_out2':i.get('run_cmd_out2','')})
       if r['cm_return']>0: return r
       run_cmd=r['run_cmd']
    elif i.get('run_cmd','')!='':
       run_cmd=i['run_cmd']

       if i.get('run_cmd_out1','')!='': run_cmd+=' 1>'+i['run_cmd_out1']
       if i.get('run_cmd_out2','')!='': run_cmd+=' 2>'+i['run_cmd_out2']
    elif i.get('binary_name','')!='' or i.get('run_cmd_name','')!='' or i.get('run_cmd_key','')!='': 
       run_time={}

       rcmd=''
       if i.get('run_cmd_key','')!='':
          r=prepare_cmd({'code_module_uoa':i.get('work_dir_module_uoa',''),
                         'code_data_uoa':i.get('work_dir_data_uoa',''),
                         'run_cmd_key':i.get('run_cmd_key',''),
                         'dataset_uoa':i.get('dataset_uoa',''),
                         'os_uoa':target_os_uoa})
          if r['cm_return']>0: return r
          run_time=r['run_time']
          for j in run_time.get('run_input_files',[]):
              if j not in run_input_files: run_input_files.append(j)

          run_set_env2=i.get('run_set_env2',{})
          if len(run_time.get('run_set_env2',{}))>0: run_set_env2.update(run_time['run_set_env2'])
          i['run_set_env2']=run_set_env2

          if run_time.get('run_script','')!='':
             if vrb=='yes':
                cm_kernel.print_for_con('')
                cm_kernel.print_for_con('Using script '+run_time['run_script'])

             ii={'run_script':run_time['run_script'],
                 'run_script_uoa':run_time.get('run_script_uoa',''),
                 'target_os_cfg':target_os_cfg,
                 'run_cmd':i.get('run_cmd',''),
                 'run_cmd_out1':i.get('run_cmd_out1',''),
                 'run_cmd_out2':i.get('run_cmd_out2','')}
             if ii['run_cmd_out1']=='': ii['run_cmd_out1']=run_time.get('run_cmd_out1','')
             if ii['run_cmd_out2']=='': ii['run_cmd_out2']=run_time.get('run_cmd_out2','')
             r=prepare_sub_script(ii)
             if r['cm_return']>0: return r
             rcmd=r['run_cmd']

       if i.get('run_cmd1','')!='': run_time['run_cmd1']=i['run_cmd1']
       if i.get('binary_name','')!='': run_time['binary_name']=i['binary_name']
       elif i.get('run_cmd_name','')!='': run_time['run_cmd_name']=i['run_cmd_name']
       if i.get('run_cmd2','')!='': run_time['run_cmd2']=i['run_cmd2']
       if i.get('run_cmd_main','')!='': run_time['run_cmd_main']=i['run_cmd_main']
       if i.get('run_cmd_out1','')!='': run_time['run_cmd_out1']=i['run_cmd_out1']
       if i.get('run_cmd_out2','')!='': run_time['run_cmd_out2']=i['run_cmd_out2']

       if len(run_time.get('run_output_files',[]))>0 and ('run_output_files' not in i or len(i['run_output_files'])==0):
          i['run_output_files']=run_time['run_output_files']

       run_cmd=''
       run_name=''
       if 'run_cmd1' in run_time:         run_cmd+=' '+run_time['run_cmd1']
       if 'binary_name' in run_time:      run_cmd+=' '+run_time['binary_name'];    run_name=run_time['binary_name']
       elif 'run_cmd_name' in run_time:   run_cmd+=' '+run_time['run_cmd_name'];   run_name=run_time['run_cmd_name']
       if 'run_cmd2' in run_time:         run_cmd+=' '+run_time['run_cmd2']
       if 'run_cmd_main' in run_time:     run_cmd+=' '+run_time['run_cmd_main']
       if 'run_cmd_out1' in run_time:     run_cmd+=' 1>'+run_time['run_cmd_out1']; i['run_cmd_out1']=run_time['run_cmd_out1']
       if 'run_cmd_out2' in run_time:     run_cmd+=' 2>'+run_time['run_cmd_out2']; i['run_cmd_out2']=run_time['run_cmd_out2']

       if rcmd!='':
          e1a['CM_RUN_CMD1']=run_time.get('run_cmd1','')
          e1a['CM_RUN_CMD2']=run_time.get('run_cmd2','')
          e1a['CM_RUN_NAME']=run_name
          e1a['CM_RUN_CMD_MAIN']=run_time.get('run_cmd_main','')
          run_cmd=rcmd

    else:
        return {'cm_return':1, 'cm_error':'not enough parameters to run code in "code run"'}

    if vrb=='yes':
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Prepared command line:')
       cm_kernel.print_for_con('  '+run_cmd)

    # Check commands after
    run_commands_after=[]
    if 'run_commands_after' in i: run_commands_after=i['run_commands_after']

    # Check that executable exists
    if run_name!='' and not os.path.isfile(run_name):
       if vrb=='yes':
          cm_kernel.print_for_con('Can\'t find executable '+run_name)
       return {'cm_return':0, 'failed_run':'yes'}

    # Prepare environment before code deps
    # First, set fixed ones
    if 'family' in target_os_cfg: e1a['CM_OS_FAMILY']=target_os_cfg['family']
    if 'bits' in target_os_cfg: e1a['CM_OS_BITS']=target_os_cfg['bits']
    if 'version' in target_os_cfg: e1a['CM_OS_VERSION']=target_os_cfg['version']
    if 'lib_dir' in target_os_cfg: e1a['CM_OS_LIB_DIR']=target_os_cfg['lib_dir']

    if 'run_set_env1' in i: e1a.update(i['run_set_env1'])
    e1a.update(processor_params)

    # Prepare script name
    script=''
    if 'exec_prefix' in target_os_cfg and target_os_cfg['exec_prefix']!='': script+=target_os_cfg['exec_prefix']
    script+=ini['cfg']['cm_batch_script_ext']

    r=cm_kernel.gen_uid({})
    if r['cm_return']>0: return r
    script+=r['cm_uid']

    # Create script  *****************************************************************************************
    ii={'script_name':script,
        'target_os_uoa':target_os_uoa,
        'set_env1':e1a}
    if 'code_deps' in i and i.get('skip_code_deps','')!='yes':
       ii['code_deps']=i['code_deps']
    if 'run_set_env2' in i and i['run_set_env2']!='':  ii['set_env2']=i['run_set_env2']
    if 'run_commands_before' in i:                     ii['run_commands_before']=i['run_commands_before']
    if run_cmd!='':                                    ii['run_cmd']=run_cmd
    if len(run_commands_after)>0:                      ii['run_commands_after']=run_commands_after
    r=prepare_script(ii)
    if r['cm_return']>0: return r
    script=r['cm_path']

    # Check if remote
    if remote:
       fail=False

    if remote and 'remote_init' in target_os_cfg:
       sys.stdout.flush()
       if vrb=='yes':
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Initializing remote device ...')
       p=target_os_cfg['remote_init']; cm_kernel.print_for_con(p); x=os.system(p)
       if x!=0: fail=True

       if not fail:
          if vrb=='yes':
             cm_kernel.print_for_con('')
             cm_kernel.print_for_con('Copying files to device ...')
          if target_os_cfg.get('no_script_execution','')!='yes': files.append(script)
          if run_name!='': files.append(run_name)
          if len(run_input_files)>0: 
             for x in run_input_files: 
                 if x not in files: files.append(x)

          for z in files: 
              filename=os.path.basename(z)
              p=target_os_cfg['remote_push']+' '+host_os_cfg['env_quotes']+z+host_os_cfg['env_quotes']+\
                ' '+target_os_cfg['remote_dir']+target_os_cfg['dir_sep']+filename
              if vrb=='yes':
                 cm_kernel.print_for_con('  '+p)
              x=os.system(p)
              if x!=0: 
                 fail=True
                 if vrb=='yes':
                    cm_kernel.print_for_con('')
                    cm_kernel.print_for_con('Error: Couldn\'t copy all necessary files for a run!')

       if not fail and run_name!='' and 'set_executable' in target_os_cfg:
          if vrb=='yes':
             cm_kernel.print_for_con('')
             cm_kernel.print_for_con('Setting permissions for binary ...')

          filename=run_name
          if remote: filename=os.path.basename(run_name)

          p=target_os_cfg['remote_shell']+' '+target_os_cfg['set_executable']+' '+target_os_cfg['remote_dir']+\
            target_os_cfg['dir_sep']+filename
          if vrb=='yes':
             cm_kernel.print_for_con('  '+p)
          x=os.system(p)
          if x!=0: fail=True

          if target_os_cfg.get('no_script_execution', '')!='yes':
             p=target_os_cfg['remote_shell']+' '+target_os_cfg['set_executable']+' '+target_os_cfg['remote_dir']+\
               target_os_cfg['dir_sep']+script
             if vrb=='yes':
                cm_kernel.print_for_con('  '+p)
             x=os.system(p)
             if x!=0: fail=True

    # Clean output files 
    if remote:
       # if remote and run_cmd_out1/run_cmd_out2 !='', add to run_output_files 
       # to get them from remote device
       if i.get('run_cmd_out1','')!='' or i.get('run_cmd_out2','')!='':
          if len(i.get('run_output_files',[]))==0: i['run_output_files']=[]
          if i.get('run_cmd_out1','')!='' and i['run_cmd_out1'] not in i['run_output_files']: i['run_output_files'].append(i['run_cmd_out1'])
          if i.get('run_cmd_out2','')!='' and i['run_cmd_out2'] not in i['run_output_files']: i['run_output_files'].append(i['run_cmd_out2'])
    else:
       if i.get('run_cmd_out1','')!='':
          try:
             os.remove(i['run_cmd_out1'])
          except:
             pass
       if i.get('run_cmd_out2','')!='':
          try:
             os.remove(i['run_cmd_out2'])
          except:
             pass

    if 'run_output_files' in i and len(i['run_output_files'])>0: 
       if vrb=='yes':
          sys.stdout.flush()
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Deleting output files ...')
       for z in i['run_output_files']:
           if vrb=='yes':
              cm_kernel.print_for_con('  '+z)

           if remote:
              p=target_os_cfg['remote_shell']+' '+target_os_cfg['delete_file']+' '+host_os_cfg['env_quotes']+target_os_cfg['remote_dir']+\
                target_os_cfg['dir_sep']+z+host_os_cfg['env_quotes']
              if vrb=='yes':
                 cm_kernel.print_for_con('     '+p)
              x=os.system(p)
              # Ignore errors
              # if x!=0: fail=True

           else:
              try:
                 os.remove(z)
              except:
                 pass

    # Run cmd
    cmd=''
    if target_os_cfg.get('no_script_execution','')=='yes':
       r=cm_kernel.load_array_from_file({'cm_filename':script})
       if r['cm_return']>0: return r
       a=r['cm_array']
       for x in a:
           xx=x.strip()
           if xx!='' and not xx.startswith(target_os_cfg['rem']):
              if cmd!='': cmd+=target_os_cfg['env_separator']+' '
              cmd+=xx
    else:
       # FGG: this was originally, (we used . ./script) but Abdul reported many problems 
       # on UBUNTU and Debian when running scripts with variable substitution (MILEPOST GCC, for example)
       # cmd=target_os_cfg['env_call']+' '+script
       if target_os_cfg.get('set_executable','')!='':
          cmd=target_os_cfg['set_executable']+' '+script+' '+target_os_cfg['env_separator']+' '+script
       else:
          # for Windows like
          cmd=target_os_cfg['env_call']+' '+script

    if remote:
       cmd=target_os_cfg['change_dir']+' '+target_os_cfg['remote_dir']+\
            target_os_cfg['env_separator']+' '+cmd
       if host_os_cfg.get('env_quotes_if_remote','')!='':
          cmdx1=cmd.replace(host_os_cfg['env_quotes_if_remote'], '\\'+host_os_cfg['env_quotes_if_remote'])
          cmdx=host_os_cfg['env_quotes_if_remote']+cmdx1+host_os_cfg['env_quotes_if_remote']
       else:
          cmdx=cmd

       if host_os_cfg.get('env_dollar_if_remote','')=='yes':
          cmdx=cmdx.replace('$','\\$')

       cmd=target_os_cfg['remote_shell']+' '+cmdx

    ii={'cmd':cmd}
    if 'run_timeout' in i and i['run_timeout']!='': ii['timeout']=i['run_timeout']
    r=-1
    fail=False

    sys.stdout.flush()
    if 'calming_delay' in i: 
       calming_delay=i['calming_delay']
    else:
       calming_delay=ini['cfg'].get('calming_delay','')

    if calming_delay!='' and float(calming_delay)!=0:
       if vrb=='yes':
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Calming delay: '+calming_delay+' second(s) ...')
       time.sleep(float(calming_delay))

    if vrb=='yes':
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Executing script:')
       cm_kernel.print_for_con('  '+cmd)

    start_time=time.time()
    rx=cm_kernel.system(ii)
    t=time.time()-start_time

    sys.stdout.flush()

    ii={'cm_return':0}

    if rx['cm_return']==1: # timeout
       ii.update({'timed_out':'yes', 'failed_run':'yes'})
    elif rx['cm_return']>0: return rx # Module error
    else: 
       ts="%.3f" % t
       rc=rx['cm_return_code']
       ii.update({'run_time_by_module':ts, 'exit_code':rc})
       if rc!=0: ii.update({'failed_run':'yes'})

    ii['run_cmd']=run_cmd

    # Moving back output files if needed
    if remote and 'run_output_files' in i and len(i['run_output_files'])>0: 
       if vrb=='yes':
          sys.stdout.flush()
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Copying output files from remote device ...')
       for z in i['run_output_files']:
           if vrb=='yes':
              cm_kernel.print_for_con('  '+z)

           filename=os.path.basename(z)
           p=target_os_cfg['remote_pull']+' '+target_os_cfg['remote_dir']+target_os_cfg['dir_sep']+filename+\
             ' '+host_os_cfg['env_quotes']+z+host_os_cfg['env_quotes']
           if vrb=='yes':
              cm_kernel.print_for_con('  '+p)
           x=os.system(p)
           if x!=0: fail=True

    # Cleaning up tmp and other files
    if i.get('keep_all_files','')!='yes':
       if vrb=='yes':
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Cleaning up local files ...')
       # clean up script if not from cM

       try:
          os.remove(script)
       except:
          pass

       if remote:
          if vrb=='yes':
             cm_kernel.print_for_con('')
             cm_kernel.print_for_con('Cleaning up files on remote device ...')
          # files already exist - add output files if needed
          if 'run_output_files' in i and len(i['run_output_files'])>0: 
             for x in i['run_output_files']: 
                 if x not in files: files.append(x)

          for z in files:
              filename=os.path.basename(z)
              p=target_os_cfg['remote_shell']+' '+target_os_cfg['delete_file']+' '+host_os_cfg['env_quotes']+target_os_cfg['remote_dir']+\
                target_os_cfg['dir_sep']+filename+host_os_cfg['env_quotes']
              if vrb=='yes':
                 cm_kernel.print_for_con('     '+p); x=os.system(p)

    if vrb=='yes':
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Run time (by module): '+ts)

    ii['work_dir']=work_dir
    ii['run_output_files']=i.get('run_output_files',[])

    if vrb=='yes':
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Execution finished!')

    return ii

# ============================================================================
def prepare_env_for_all_codes(i):

    """
    Prepare environment for all codes

    Input:  {
              code_deps       - list with code UOA for dependencies [{"index":"uoa"} ...]
              os_uoa          - OS UOA
              no_strict_check - if 'yes', do not check if code dependency was installed properly
            }

    Output: {
              cm_return      - return code = 0, if successful
              cm_string      - environment string
              cm_array       - array with environment setting (for scripts)
              include_paths1 - list with paths with include directories
              lib_paths      - list with libraries 
              env_separator  - environment separator (just in case to avoid double loading of OS)
            }
    """

    # Check vars
    if 'code_deps' not in i: return {'cm_return':1, 'cm_error':'"code_deps" is not defined in "code prepare_env_for_all_codes"'}

    include_paths=[]
    lib_paths=[]

    # Load OS
    os_uoa=''
    if 'os_uoa' in i and i['os_uoa']!='': os_uoa=i['os_uoa']
    elif 'cm_default_os_uoa' in cm_kernel.ini['dcfg'] and cm_kernel.ini['dcfg']['cm_default_os_uoa']!='':
       os_uoa=cm_kernel.ini['dcfg']['cm_default_os_uoa']

    if os_uoa=='' not in i:
       return {'cm_return':1, 'cm_error':'"os_uoa" is not defined and not in kernel'}

    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['os'],
        'cm_action':'load',
        'cm_data_uoa':os_uoa}
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    os_cfg=r['cm_data_obj']['cfg']
    os_path=r['cm_path']
    os_uid=r['cm_uid']
    os_alias=r['cm_alias']

    s_code_deps=''
    a_code_deps=[]
    if 'code_deps' in i:
       for xx in i['code_deps']:
           yy=xx.keys()[0]
           x=xx[yy]

           if x=='':
              return {'cm_return':1, 'cm_error':'dependency "'+yy+'" is empty, please check your input'}

           # Check if code was installed
           if i.get('no_strict_check','')!='yes':
              ii={'cm_run_module_uoa':ini['cm_module_uid'],
                  'cm_action':'load',
                  'cm_data_uoa':x}
              r=cm_kernel.access(ii)
              if r['cm_return']==16:
                 return {'cm_return':1, 'cm_error':'dependency is not resolved - code '+x+' ('+yy+') is not installed'}
              elif r['cm_return']>0: return r
              code_cfg=r['cm_data_obj']['cfg']
              if code_cfg.get('build_finished_successfully','')!='yes':
                 return {'cm_return':1, 'cm_error':'dependency is not resolved - code '+x+' ('+yy+') is not installed'}

              code_path=r['cm_path']
              include_paths.append(os.path.join(code_path, 'include'))

              if 'state_input' in code_cfg and \
                 'run_set_env2' in code_cfg['state_input'] and \
                 'CM_TARGET_FILE' in code_cfg['state_input']['run_set_env2']:
                 lib_paths.append(os.path.join(code_path, os_cfg['lib_dir'], 
                       code_cfg['state_input']['run_set_env2']['CM_TARGET_FILE']))

           # Environment script
           r=get_env({'cm_data_uoa':x, 'os_uoa':os_uoa})
           if r['cm_return']>0: return r

#           z=os_cfg['env_call']+' '+os.path.join(cm_kernel.ini[cm_kernel.env_cm_bin],r['cm_string'])
           z1=os_cfg['env_set']+' '+yy+'='+os_cfg['env_quotes']+x+os_cfg['env_quotes']
           z=os_cfg['env_call']+' '+r['cm_string']

           if s_code_deps!='': s_code_deps+=' '+os_cfg['env_separator']+' '
           s_code_deps+=z1
           if s_code_deps!='': s_code_deps+=' '+os_cfg['env_separator']+' '
           s_code_deps+=z
           # FGG added again setting environment variable since calling other scripts can change it
           # for example, we set CM_CODE_DEP_COMPILER and then call GMP that was compiled with another
           # compiler, then it will change this variable to a wrong value and further tools will 
           # not be working correctly ...
           if s_code_deps!='': s_code_deps+=' '+os_cfg['env_separator']+' '
           s_code_deps+=z1

           a_code_deps.append(z1)
           a_code_deps.append(z)
           a_code_deps.append(z1)

    return {'cm_return':0, 'cm_string':s_code_deps, 'cm_array':a_code_deps, 'env_separator': os_cfg['env_separator'],
                           'include_paths':include_paths, 'lib_paths':lib_paths}

# ============================================================================
def prepare_env_vars(i):
    """
    Prepare environment variables

    Input:  {
              array      - array of environment variables to set
              prefix     - add prefix to set environment variable
              separator  - add separator for the command line
              (quotes)   - use quotes?
            }

    Output: {
              cm_return   - if =0, success
              cm_string   - cmd with prepared environment (export A=B; export C=D; ...)
              cm_string1  - simplified string (CM_ALL_ENV="A=B C=D E=F")
              cm_array    - array with environment setting (for scripts)
            }
    """

    # Check vars
    if 'array' not in i: return {'cm_return':1, 'cm_error': '"array" is not set in "os prepare_env_vars"'}
    if 'prefix' not in i: return {'cm_return':1, 'cm_error': '"prefix" is not set in "os prepare_env_vars"'}
    if 'separator' not in i: return {'cm_return':1, 'cm_error': '"separator" is not set in "os prepare_env_vars"'}

    q=''
    if 'quotes' in i: q=i['quotes']

    a=[]
    s=''
    s1=i['prefix']+' CM_ALL_ENV='+q

    for k,v in i['array'].iteritems():
        if s!='': 
           s+=' '+i['separator']+' '
           s1+=' '

        z=i['prefix']+' '+k+'='

        # Check quotes (a bit tricky depending on the OS)
        x=''
        if q!='':
           # likely Linux/Android
           x=q+v.replace('"', '\"')+q
        else:
           # likely Windows
           x=v

        s+=z+x
        a.append(z+x)

        s1+=k+'='+q+v+q
    s1+=q

    return {'cm_return':0, 'cm_string':s, 'cm_string1':s1, 'cm_array':a}

# ============================================================================
def set_env(i):

    """
    Set environment for a given code

    Input:  {
              input_key  - key with code_uoa
            }

    Output: {
              cm_return  - return code = 0, if successful
              os_env     - OS environment from the code
            }
    """

    # Check vars
    if 'input_key' not in i: return {'cm_return':1, 'cm_error':'"input_key" is not defined in "code set_env"'}
    if i['input_key'] not in i: return {'cm_return':1, 'cm_error':'i["input_key"] is not defined in "code set_env"'}

    code_uoa=i[i['input_key']]

    # Load code
    ii={'cm_run_module_uoa':ini['cm_module_uid'],
        'cm_action':'load',
        'cm_data_uoa':code_uoa}
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r
    code_cfg=r['cm_data_obj']['cfg']

    r={'cm_return':0}

    if 'os_env' in code_cfg: r.update({'os_env':code_cfg['os_env']})

    return r

# ============================================================================
def install(i):

    """
    Install code and set environment

    Input:  {
              (install_data_uid)              - create an entry with this UID
              (install_data_alias)            - create an entry with this alias
              (install_data_display_as_alias) - use this display as alias for a generated entry
              (install_module_uoa)            - use this module to create an entry (if not set, use 'code')
              (install_repo_uoa)              - use this repo to create an entry
              (cm_array)                      - add this data to the new entry
              target_os_uoa                   - target os to install script
              (add_rem_to_script)             - add rem to install script
            }

    Output: {
              cm_return  - return code = 0, if successful

              Parameters from entry creation

              script_filename - script filename
              script_name     - full script name
            }
    """

    cm_kernel.print_for_con('***********************************************')
    cm_kernel.print_for_con('Installing code ...')

    # Check vars
    if 'target_os_uoa' not in i: return {'cm_return':1, 'cm_error':'"target_os_uoa" is not defined in "code install"'}

    # Create entry
    ii={'cm_run_module_uoa':ini['cm_module_uid'],
        'cm_action':'update'}
    if 'install_data_uid' in i and i['install_data_uid']!='': 
       ii['cm_data_uid']=i['install_data_uid']
    if 'install_data_alias' in i and i['install_data_alias']!='': 
       ii['cm_data_uoa']=i['install_data_alias']
    if 'install_data_display_as_alias' in i: 
       ii['cm_display_as_alias']=i['install_data_display_as_alias']
    if 'install_module_uoa' in i and i['install_module_uoa']!='':
       ii['cm_run_module_uoa']=i['install_module_uoa']
    if 'cm_array' in i and len(i['cm_array'])>0: ii['cm_array']=i['cm_array']
    if 'install_repo_uoa' in i and i['install_repo_uoa']!='': 
       ii['cm_repo_uoa']=i['install_repo_uoa']
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    target_path=r['cm_path']
    target_uid=r['cm_uid']
    target_alias=r['cm_alias']

    # Prepare script
    rx=get_env({'cm_data_uoa':target_uid,
                'os_uoa':i['target_os_uoa']})
    if rx['cm_return']>0: return rx

    script=rx['cm_string']

    ii={'script_name':script,
        'skip_extension':'yes',
        'target_os_uoa':i['target_os_uoa'],
        'cm_path':target_path}
    if 'code_deps' in i and i.get('skip_code_deps','')!='yes':
       ii['code_deps']=i['code_deps']

    # Add remark about how code was built
    if 'add_rem_to_script' in i:
       run_commands_before=[]
       run_commands_before.append('')
       for x in i['add_rem_to_script']:
           run_commands_before.append(x)
       ii['run_commands_before']=run_commands_before

    rx=prepare_script(ii)
    if rx['cm_return']>0: return rx

    r['script_name']=rx['cm_path']
    r['script_filename']=script

    return r

# ============================================================================
def prepare_script(i):

    """
    Prepare script with code deps

    Input:  {
              script_name           - script name (usually without extensions)
              target_os_uoa         - target os to get script extension and other parameters
              (skip_extension)      - if 'yes', script already has extension
              (cm_path)             - path to create script
              (set_env1)            - add environment vars (1) to script
              (code_deps)           - add code deps to script
              (set_env2)            - add environment vars (2) to script
              (run_commands_before) - add some commands before main command
              (run_cmd)             - add main command
              (run_commands_after)  - add some commands after main command
            }

    Output: {
              cm_return  - return code = 0, if successful
              cm_path    - full name of the created script with path
            }
    """

    # Check vars
    if 'script_name' not in i: return {'cm_return':1, 'cm_error':'"script_name" is not defined in "code prepare_script"'}
    if 'target_os_uoa' not in i: return {'cm_return':1, 'cm_error':'"target_os_uoa" is not defined in "code prepare_script"'}

    # Prepare path
    p=''
    if 'cm_path' in i and i['cm_path']!='':
       p=os.path.join(i['cm_path'], i['script_name'])
    else:
       p=i['script_name']

    # Load OS
    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['os'],
        'cm_action':'load',
        'cm_data_uoa':i['target_os_uoa']}
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    target_os_cfg=r['cm_data_obj']['cfg']
    target_os_path=r['cm_path']
    target_os_uid=r['cm_uid']
    target_os_alias=r['cm_alias']

    if i.get('skip_extension','')!='yes':
       p+=target_os_cfg['script_ext']

    try:
       f=open(p, 'w')
       if 'batch_prefix' in target_os_cfg and target_os_cfg['batch_prefix']!='': f.write(target_os_cfg['batch_prefix'])

       if 'rem' in target_os_cfg: f.write('\n'+target_os_cfg['rem']+' target_os_uoa: '+i['target_os_uoa']+'\n')

       if 'set_env1' in i and len(i['set_env1'])>0:
          f.write('\n')
          if 'rem' in target_os_cfg: f.write(target_os_cfg['rem']+' Set global parameters\n')
          r=prepare_env_vars({'array':i['set_env1'],
                              'prefix':target_os_cfg['env_set'],
                              'separator':target_os_cfg['env_separator'],
                              'quotes':target_os_cfg['env_quotes']})
          if r['cm_return']>0: return r
          for x in r['cm_array']: f.write(x+'\n')

       if 'code_deps' in i and len(i['code_deps'])>0:
          r=prepare_env_for_all_codes({'code_deps':i['code_deps'],
                                       'os_uoa':i['target_os_uoa']})
          if r['cm_return']>0: return r
          f.write('\n')
          if 'rem' in target_os_cfg: f.write(target_os_cfg['rem']+' Prepare code dependencies\n')
          for x in r['cm_array']: f.write(x+'\n')

       if 'set_env2' in i and len(i['set_env2'])>0:
          f.write('\n')
          if 'rem' in target_os_cfg: f.write(target_os_cfg['rem']+' Set execution parameters\n')
          r=prepare_env_vars({'array':i['set_env2'],
                              'prefix':target_os_cfg['env_set'],
                              'separator':target_os_cfg['env_separator'],
                              'quotes':target_os_cfg['env_quotes']})
          if r['cm_return']>0: return r
          for x in r['cm_array']: f.write(x+'\n')

       if 'run_commands_before' in i:
          for x in i['run_commands_before']: f.write(x+'\n')

       if 'run_cmd' in i:
          f.write('\n')
          if 'rem' in target_os_cfg: f.write(target_os_cfg['rem']+' Executable\n')
          f.write(i['run_cmd'].strip()+'\n')

       if 'run_commands_after' in i:
          for x in i['run_commands_after']: f.write(x+'\n')

       f.close()
    except Exception as e:
       return {'cm_return':1, 'cm_error':'error while preparing script in "code prepare_script" ('+format(e)+')'}

    return {'cm_return':0, 'cm_path':p}

# ============================================================================
def prepare_sub_script(i):

    """
    Prepare sub_script with extension

    Input:  {
              run_script           - script name (usually without extensions)
              (run_script_uoa)     - script UOA if any
              target_os_cfg        -  target os cfg to get script extension and other parameters

            }

    Output: {
              cm_return  - return code = 0, if successful
              cm_path    - full name of the created script with path
            }
    """

    run_cmd=''

    target_os_cfg=i['target_os_cfg']

    remote=False
    if target_os_cfg.get('remote','')=='yes': 
       remote=True

    script_name=i['run_script']

    script_path=''
    if 'run_script_uoa' in i and i['run_script_uoa']!='':
#       cm_kernel.print_for_con('')
#       cm_kernel.print_for_con('Preparing path for OS script '+i['run_script_uoa']+' ...')

       ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['os.script'],
           'cm_action':'load',
           'cm_data_uoa':i['run_script_uoa']}
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r

       script_cfg=r['cm_data_obj']['cfg']
       script_path=r['cm_path']

       if 'scripts' not in script_cfg or i['run_script'] not in script_cfg['scripts']:
          return {'cm_return':1, 'cm_error':'can\'t find script in os.script configuration'}

       script_name=script_cfg['scripts'][script_name]

    script_name+=target_os_cfg['script_ext']

    run_name=script_name
    if script_path!='':
       run_name=os.path.join(script_path, run_name)
    elif 'exec_prefix' in target_os_cfg and target_os_cfg['exec_prefix']!='': 
       run_name=target_os_cfg['exec_prefix']+run_name

    if target_os_cfg.get('set_executable','')!='':
       p=target_os_cfg['set_executable']+' '+run_name
       x=os.system(p)

    run_cmd=''
    if remote and target_os_cfg.get('no_script_execution','')=='yes':
       r=cm_kernel.load_array_from_file({'cm_filename':run_name})
       if r['cm_return']>0: return r
       a=r['cm_array']
       for x in a:
           xx=x.strip()
           if xx!='' and not xx.startswith(target_os_cfg['rem']):
              if run_cmd!='': run_cmd+=target_os_cfg['env_separator']+' '
              run_cmd+=xx
       run_name=''
    else:
       run_cmd=run_name

    if i.get('run_cmd','')!='': run_cmd+=' '+i['run_cmd']

    if i.get('run_cmd_out1','')!='': run_cmd+=' 1>'+i['run_cmd_out1']
    if i.get('run_cmd_out2','')!='': run_cmd+=' 2>'+i['run_cmd_out2']


    return {'cm_return':0, 'run_cmd':run_cmd}

# ============================================================================
def prepare_cmd(i):
    """
    Prepare command line for the code

    Input:  {
              (code_module_uoa)  - module of the working data
              (code_data_uoa)    - working data uoa
              (run_cmd_key)      - name if multiple CMDs available for this program
              (dataset_uoa)      - UOA of dataset used to prepare this cmd
              (os_uoa)           - OS UOA
              (compilation_type) - static or dynamic
            }

    Output: {
              cm_return               - if =0, success
              (cm_error)              - if cm_return>0, error text

              run_time={
                run_env               - set environment before command line
                                      - the following params will be aggregated to 1 line
                run_cmd1
                run_cmd_binary_name
                run_cmd2
                run_cmd_main
                run_cmd3
                run_cmd_out1
                run_cmd_out2
                run_output_files
                run_input_files
                dataset_files
              }

              build_compiler_vars     - possible compiler variables (often set hardwired dataset)
            }
    """

    # Prepare environment
    rr={'cm_return':0}

    # Load OS configuration
    os_uoa=''
    if 'os_uoa' in i and i['os_uoa']!='': os_uoa=i['os_uoa']
    elif 'cm_default_os_uoa' in cm_kernel.ini['dcfg'] and cm_kernel.ini['dcfg']['cm_default_os_uoa']!='':
       os_uoa=cm_kernel.ini['dcfg']['cm_default_os_uoa']

    if os_uoa=='' not in i:
       return {'cm_return':1, 'cm_error':'"os_uoa" is not defined and not in kernel'}
    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['os'],
        'cm_action':'load',
        'cm_data_uoa':os_uoa}
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    os_cfg=r['cm_data_obj']['cfg']
    os_path=r['cm_path']
    os_uid=r['cm_uid']
    os_alias=r['cm_alias']

    run_time={}
    run_input_files=[]
    target_file=''

    # Check vars
    if 'code_data_uoa' in i and 'run_cmd_key' in i:
       # Load source code
       m=ini['cm_module_uid']
       if 'code_module_uoa' in i and i['code_module_uoa']!='': m=i['code_module_uoa']
       ii={'cm_run_module_uoa':m,
           'cm_action':'load',
           'cm_data_uoa':i['code_data_uoa']}
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r

       sc_cfg=r['cm_data_obj']['cfg']
       sc_path=r['cm_path']
       sc_uid=r['cm_uid']
       sc_alias=r['cm_alias']

       # Prepare binary file
       target_file=''
       if 'target_file' in sc_cfg: target_file=os_cfg.get('exec_prefix','')+sc_cfg['target_file']

       add_target_extension1=sc_cfg.get('add_target_extension',{})
       ct=i.get('compilation_type','')
       if ct=='': ct='static'
       if ct in add_target_extension1: add_target_extension=add_target_extension1.get(ct)

       if add_target_extension!='':
          if 'file_extensions' in os_cfg and add_target_extension in os_cfg['file_extensions']:
             target_ext=os_cfg['file_extensions'][add_target_extension]
             target_file+=target_ext

       cm_kernel.print_for_con('Prepared target binary name: '+target_file)

       # Set vars
       if 'run_cmds' in sc_cfg and i['run_cmd_key'] in sc_cfg['run_cmds']:
          rc=sc_cfg['run_cmds'][i['run_cmd_key']]

          run_time=copy.deepcopy(rc.get('run_time',{})) # otherwise change somewhere 
                                                        # and it mixes up caching

       # Put original input files (useful for mobiles not to mix with dataset files)
       orif=[]
       for q in run_time.get('run_input_files',[]):
           orif.append(q)

       # Load dataset
       if i.get('dataset_uoa','')!='':
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Loading dataset ...')
          ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['dataset'],
              'cm_action':'load',
              'cm_data_uoa':i['dataset_uoa']}
          r=cm_kernel.access(ii)
          if r['cm_return']>0: return r

          ds_cfg=r['cm_data_obj']['cfg']
          ds_path=r['cm_path']
          ds_uid=r['cm_uid']
          ds_alias=r['cm_alias']

          if 'build_compiler_vars' in ds_cfg:
             rr['build_compiler_vars']=ds_cfg['build_compiler_vars']

          if 'run_cmd_main' in run_time: 
             ds_path1=ds_path
             os_sep=os_cfg.get('dir_sep','')
             if os_cfg.get('remote','')=='yes': 
                ds_path1=''
                os_sep=''
             run_time['run_cmd_main']=run_time['run_cmd_main'].replace(cm_kernel.convert_str_to_special('dataset_path'), ds_path1)
             run_time['run_cmd_main']=run_time['run_cmd_main'].replace(cm_kernel.convert_str_to_special('os_dir_separator'), os_sep)

             # Check which path to use for data set
             if 'dataset_files' in ds_cfg and len(ds_cfg['dataset_files'])>0:
                run_time['dataset_files']=ds_cfg['dataset_files']
                xx=0
                for x in ds_cfg['dataset_files']:
                    y='dataset_filename'
                    if xx!=0: y+='_'+str(xx)
                    run_time['run_cmd_main']=run_time['run_cmd_main'].replace(cm_kernel.convert_str_to_special(y), x)
                    xx+=1

          # Prepare input files (for remote)
          if 'dataset_files' in ds_cfg and len(ds_cfg['dataset_files'])>0:
              x1=ds_path
              for x2 in ds_cfg['dataset_files']:
                  x3=os.path.join(x1,x2)
                  if x3 not in run_input_files: run_input_files.append(x3)

          # Check cm_properties
          rcm=ds_cfg.get('cm_properties',{}).get('run_time',{}).get('run_cmd_main',{})
          for x in rcm:
              run_time['run_cmd_main']=run_time['run_cmd_main'].replace(cm_kernel.convert_str_to_special(x), rcm[x])

    run_time['binary_name']=target_file
    rr['run_time']=run_time
    rr['run_time']['original_run_input_files']=orif
    if 'run_input_files' not in rr['run_time']: rr['run_time']['run_input_files']=[]
    for q in run_input_files:
        if q not in rr['run_time']['run_input_files']: rr['run_time']['run_input_files'].append(q)

    return rr

# ============================================================================
def native_run(i):
    """
    Native run with timing

    Input:  {
              cm_unparsed - run
              skip_output - if 'yes', do not print 'Execution time ...'
            }

    Output: {
              cm_return      - return of the system
              execution_time - execution time of a command
            }
    """

    ucmd=i['cm_unparsed']

    cmd=''
    for q in ucmd:
        cmd+=' '+q
    cmd=cmd.strip()

    tstart=time.time()

    rc=os.system(cmd)

    t=time.time()-tstart

    if i.get('skip_output','')!='yes':
       cm_kernel.print_for_con('Execution time: '+"%.3f" % t+' seconds')

    return {'cm_return':0, 'execution_time':str(t)}
