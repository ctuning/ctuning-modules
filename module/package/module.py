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
import shutil
import os
import json
import re

# ============================================================================
def init(i):
    return {'cm_return':0}

# ============================================================================
def install(i):

    """
    Install cM package

    Input:  {
              package_data_uoa                - UOA of package to install
              (package_repo_uoa)              - repo of the package
              package_host_os_uoa             - UOA of host OS (to set up script execution)

              (install_data_uid)              - UID of the code where package will be installed
                                                if install_data_uid=='' it will be randomly generated
              (install_data_alias)            - use this alias for a generated entry
              (install_data_display_as_alias) - use this display as alias for a generated entry

                If package should be built:
              build_target_os_uoa             - target OS uoa for building
              (code_deps)                     - list with code UOA for dependencies [{"index":"uoa"} ...]
              (run_target_processor_uoa)      - target processor UOA (not strictly needed - can add some helper parameters before executing code)
              (run_set_env2)                  - array with environment variables to be set before executable
              (add_rem_to_script)             - add rem to install script
              (add_to_code_entry)             - add array to code entry
              (skip_extract_and_build)        - if 'yes', skip copy, extract and build (by setting CM_SKIP_BUILD=yes)
            }

    Output: {
              cm_return - return code = 0, if successful

              Output from 'code install'
            }
    """

    cm_kernel.print_for_con('***********************************************')
    cm_kernel.print_for_con('Installing package ...')

    # Check package UOA
    if 'package_data_uoa' not in i:
       return {'cm_return':1, 'cm_error':'"package_data_uoa" is not defined'}
    package=i['package_data_uoa']

    # Load package configuration
    cm_kernel.print_for_con('')
    cm_kernel.print_for_con('Loading info about package '+package+' ...')

    ii={'cm_run_module_uoa':ini['cm_module_uid'],
        'cm_action':'load',
        'cm_data_uoa':package}
    if 'package_repo_uoa' in i: ii.update({'cm_repo_uoa':i['package_repo_uoa']})
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    package_cfg=r['cm_data_obj']['cfg']
    package_path=r['cm_path']
    package_uid=r['cm_uid']
    package_alias=r['cm_alias']

    # Set run_set_env2
    run_set_env2=package_cfg.get('run_set_env2',{})
    if 'run_set_env2' in i and len(i['run_set_env2'])>0: run_set_env2.update(i['run_set_env2'])

    cm_kernel.print_for_con('')
    cm_kernel.print_for_con('Package path:  '+package_path)
    cm_kernel.print_for_con('Package Alias: '+package_alias)
    cm_kernel.print_for_con('Package UID:   '+package_uid)

    # Check if need to add something to the code entry
    add_to_code_entry=i.get('add_to_code_entry',{})
    if 'add_to_code_entry' in package_cfg: 
       cm_kernel.merge_arrays({'cm_array':add_to_code_entry, 'cm_array1': package_cfg['add_to_code_entry']})

    # Load OS configuration
    package_host_os_uoa=''
    if 'package_host_os_uoa' in i and i['package_host_os_uoa']!='': package_host_os_uoa=i['package_host_os_uoa']
    elif 'cm_default_os_uoa' in cm_kernel.ini['dcfg'] and cm_kernel.ini['dcfg']['cm_default_os_uoa']!='':
       package_host_os_uoa=cm_kernel.ini['dcfg']['cm_default_os_uoa']

    if package_host_os_uoa=='' not in i:
       return {'cm_return':1, 'cm_error':'"package_host_os_uoa" is not defined and not in kernel'}
    cm_kernel.print_for_con('')
    cm_kernel.print_for_con('Loading os '+package_host_os_uoa+' ...')
    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['os'],
        'cm_action':'load',
        'cm_data_uoa':package_host_os_uoa}
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    target_os_cfg=r['cm_data_obj']['cfg']
    target_os_path=r['cm_path']
    target_os_uid=r['cm_uid']
    target_os_alias=r['cm_alias']

    # Check if need to build
    build=False
    if package_cfg.get('build','')=='yes': build=True

    # Check where to copy files before installing: to "code" or to "code.source"
    if build:
       # Create code source entry
       ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['code.source'],
           'cm_action':'update'}
       if 'install_data_uid' in i: 
          ii['cm_data_uoa']=i['install_data_uid']
       else:
          ii['cm_data_uoa']=package_uid
       if 'add_to_code_source' in package_cfg:
          ii['cm_array']=package_cfg['add_to_code_source']
       if 'install_repo_uoa' in i: ii['cm_repo_uoa']=i['install_repo_uoa']
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r
       target_path=r['cm_path']
       target_uoa=r['cm_uid']
    else:
       # Create code entry
       ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['code'],
           'cm_action':'update'}
       if 'install_data_uid' in i: ii.update({'cm_data_uid':i['install_data_uid']})
       if 'install_data_alias' in i: ii.update({'cm_data_uoa':i['install_data_alias']})
       if 'install_data_display_as_alias' in i: ii.update({'cm_display_as_alias':i['install_data_display_as_alias']})
       if 'install_repo_uoa' in i: ii['cm_repo_uoa']=i['install_repo_uoa']
       if 'local_src_dir' in package_cfg:
          ii['cm_array']={}
          ii['cm_array']['local_src_dir']=package_cfg['local_src_dir']
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r
       target_path=r['cm_path']
       target_uoa=r['cm_uid']

    # Install script
    install_script_without_ext=''
    install_script=''
    if 'install_script' in package_cfg:
       install_script_without_ext=package_cfg['install_script']
       install_script=install_script_without_ext+target_os_cfg['script_ext']

    # Copy files
    files=[]
    if 'cm_files' in package_cfg: files=package_cfg['cm_files']
    if install_script!='': files.append(install_script)

    if len(files)>0:
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Copying files ...')
       for f in files:
           cm_kernel.print_for_con('  '+f)
           f1=os.path.join(package_path, f)
           f2=os.path.join(target_path, f)
           try:
             shutil.copyfile(str(f1),str(f2))
           except IOError as e:
             return {'cm_return':1, 'cm_error':'can\'t copy file '+f+' ('+format(e)+')'}

    if i.get('skip_extract_and_build','')!='yes':

       # Extracting 
       if len(files)>0:
          cm_kernel.print_for_con('')
          cm_kernel.print_for_con('Check if need to extract files ...')
          for f in files:
              if f!=install_script:
                 for ext in target_os_cfg['extract_package']:
                     if f.endswith(ext):
                        s=target_os_cfg['change_dir']+' '+target_path+' '+target_os_cfg['env_separator']+\
                        target_os_cfg['extract_package'][ext]
                        s1=s.replace(cm_kernel.convert_str_to_special('cm_file'), f)
                        s2=s1.replace(cm_kernel.convert_str_to_special('cm_file_without_one_ext'), os.path.splitext(f)[0])

                        cm_kernel.print_for_con('')
                        cm_kernel.print_for_con(s2)
                        cm_kernel.print_for_con('')

                        r=os.system(str(s2))
                        if r!=0: return {'cm_return':1, 'cm_error':'problem while extracting '+f}

    # Set executable
    if install_script!='' and 'set_executable' in target_os_cfg:
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Setting permissions for executable ...')

       p1=os.path.join(target_path, install_script)
       r=os.system(target_os_cfg['set_executable']+' '+p1)

    # Build
    if build:
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Building ...')
    else:
       cm_kernel.print_for_con('')
       cm_kernel.print_for_con('Installing ...')

    if install_script=='':
       return {'cm_return':1, 'cm_error':'install script is not defined'}

    # Checking some vars
    if 'build_target_os_uoa' not in i:
       return {'cm_return':1, 'cm_error':'"build_target_os_uoa" is not defined'}

    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['code.source'],
        'package_data_uoa':i['package_data_uoa'],
        'cm_action':'build',
        'work_dir_data_uoa':target_uoa,
        'run_script':install_script_without_ext,
        'install':'yes',
        'run_host_os_uoa':i['package_host_os_uoa'],
        'build_target_os_uoa':i['build_target_os_uoa'],
        'run_set_env2':{}}
    if build:
       ii['work_dir_module_uoa']=ini['cfg']['cm_modules']['code.source']
    else:
       ii['work_dir_module_uoa']=ini['cfg']['cm_modules']['code']

    if 'install_repo_uoa' in i: 
       ii['work_dir_repo_uoa']=i['install_repo_uoa']
       ii['install_repo_uoa']=i['install_repo_uoa']
    if 'install_data_uid' in i: 
       ii['install_data_uid']=i['install_data_uid']
    else: ii['install_data_uid']=target_uoa #FGG: need to check that it's correct, i.e. if we install 
                                            #     something like GCC, that we correctly reuse code & code.source
    if 'install_data_alias' in i: ii['install_data_uoa']=i['install_data_alias']
    if 'install_data_display_as_alias' in i: ii['install_data_display_as_alias']=i['install_data_display_as_alias']
    if 'code_deps' in i: ii['code_deps']=i['code_deps']
    if len(run_set_env2)>0: ii['run_set_env2']=run_set_env2
    if i.get('skip_extract_and_build','')=='yes': ii['run_set_env2']['CM_SKIP_BUILD']='yes'
    if 'run_target_processor_uoa' in i: ii['run_target_processor_uoa']=i['run_target_processor_uoa']
    if 'add_rem_to_script' in i: ii['add_rem_to_script']=i['add_rem_to_script']
    if len(add_to_code_entry)>0: ii['add_to_code_entry']=add_to_code_entry

    rr=cm_kernel.access(ii)

    return rr

# ============================================================================
def web_install(i):

    """
    Install cM package/library

    When searching for already installed code, dependencies are checked
     * using classes for packages (to allow reuse of packages)
     * by exact code_uoa for code.source (to have exact build setup)

    FGG: the checks are a bit ugly and were done in a rush. 
         Should be simplified, cleaned up and unified one day.

    Input:  {
              package_data_uoa              - UOA of package to install
              (package_repo_uoa)            - repo of the package
              package_host_os_uoa           - UOA of host OS (to set up script execution)

              (install_data_uid)            - UID of the code where package will be installed
                                              if install_data_uid=='' it will be randomly generated
              (install_data_alias)          - use this alias for a generated entry

                If package should be built:
              build_target_os_uoa           - target OS uoa for building
              (code_deps)                   - list with code UOA for dependencies [{"index":"uoa"} ...]
              (run_target_processor_uoa)    - target processor UOA (not strictly needed - can add some helper parameters before executing code)
              (run_set_env2)                - array with environment variables to be set before executable
              (add_rem_to_script)           - add rem to install script
              (skip_extract_and_build)      - if 'yes', skip copy, extract and build (by setting CM_SKIP_BUILD=yes)
            }

    Output: {
              cm_return - return code = 0, if successful

              Output from 'code install'
            }
    """

    # Get web style
    if 'cfg' in cm_kernel.ini['web_style']: web=cm_kernel.ini['web_style']['cfg']
    else:
       return {'cm_return':1, 'cm_error':'web style is not defined'}

    cm_kernel.print_for_con('<span class="cm-title">Install / monitor packages</span><br>')

    # Detecting/restoring data from forms
    a1={}

    r=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['cm-web'],
                        'cm_action':'detect_form_params',
                        'cm_array':i, 
                        'cm_prefix':'#form1'})
    if r['cm_return']>0: return r
    cm_form_array1=r['cm_array']
    cm_form_commands1=r['cm_commands']

    # Get data description for this action
    r=cm_kernel.get_data_description({'cm_module_uoa':ini['cm_module_uoa'], 
                                      'cm_which_action':i['cm_action']})
    if r['cm_return']>0: return r
    cm_data_desc1=r['cm_data_desc']
    cm_params_default1=r['cm_params_default']

    # Check default
    if len(cm_form_array1)==0:
       a1=cm_params_default1
    else:
       r=cm_kernel.restore_flattened_array({'cm_array':cm_form_array1, 
                                            'cm_replace_in_keys':{'^35^':'#', '^64^':'@'}})
       if r['cm_return']>0: return r
       a1=r['cm_array']

    # If there is data in form, means that refresh
    forms_exists='yes'
    if len(cm_form_array1)==0: forms_exists='no'

    if 'skip_extract_and_build' in i: a1['skip_extract_and_build']=i['skip_extract_and_build']

    # Check if setup is selected and prune choices *********************************************************************
    cm_scen_c=''
    cm_scen_p=''

    cm_setup_uoa=a1.get('ctuning_setup_uoa','')
    if cm_setup_uoa!='':
       # Load setup
       ii={}
       ii['cm_run_module_uoa']=ini['cfg']['cm_modules']['ctuning.setup']
       ii['cm_action']='load'
       ii['cm_data_uoa']=cm_setup_uoa
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r

       ds=r['cm_data_obj']['cfg']

       # Check class
       ctuning_scenario_uoa=ds.get('ctuning_scenario_uoa','')
       if ctuning_scenario_uoa!='':
          ii={}
          ii['cm_run_module_uoa']=ini['cfg']['cm_modules']['ctuning.scenario']
          ii['cm_action']='load'
          ii['cm_data_uoa']=ctuning_scenario_uoa
          r=cm_kernel.access(ii)
          if r['cm_return']>0: return r
          ds1=r['cm_data_obj']['cfg']

          cm_scen_c=ds1.get('cm_classes_uoa',[])
          cm_scen_p=ds1.get('cm_properties',{})

    cm_kernel.print_for_web('<FORM ACTION="" name="add_edit" METHOD="POST" enctype="multipart/form-data" accept-charset="utf-8">' )

    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['cm-web'],
        'cm_action':'visualize_data',
        'cm_array':a1,
        'cm_data_desc':cm_data_desc1,
        'cm_form_commands':cm_form_commands1,
        'cm_separator':'#',
        'cm_separator_form':'#form1#',
        'cm_forms_exists':forms_exists,
        'cm_support_raw_edit':'no',
        'hide_add_new_object':'yes',
        'cm_mode':'add'}
    if 'cm_raw_edit' in i: ii['cm_raw_edit']=i['cm_raw_edit']
    if 'cm_back_json' in i: ii['cm_back_json']=i['cm_back_json']
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r
    cm_kernel.print_for_web(r['cm_string'])

    # Pruning vars
    cm_t_os_uoa=a1.get('build_target_os_uoa','')
    cm_h_os_uoa=a1.get('package_host_os_uoa','')
    cm_p_uoa=a1.get('run_target_processor_uoa','')
    cm_repo_uoa=a1.get('package_repo_uoa','')

    # Check target OS classes and properties
    cm_t_os_c=''
    cm_t_os_p=''
    if cm_t_os_uoa!='':
       ii={}
       ii['cm_run_module_uoa']=ini['cfg']['cm_modules']['os']
       ii['cm_action']='load'
       ii['cm_data_uoa']=cm_t_os_uoa
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r

       cm_t_os_uid=r['cm_uid']
       cm_t_os_uoa=r['cm_uoa']

       d=r['cm_data_obj']['cfg']

       cm_t_os_c=d.get('cm_classes_uoa',[])
       cm_t_os_p=d.get('cm_properties',{})

    cm_h_os_c=''
    cm_h_os_p=''
    cm_h_os_cfg={}
    if cm_h_os_uoa!='':
       ii={}
       ii['cm_run_module_uoa']=ini['cfg']['cm_modules']['os']
       ii['cm_action']='load'
       ii['cm_data_uoa']=cm_h_os_uoa
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r

       cm_h_os_uid=r['cm_uid']
       cm_h_os_uoa=r['cm_uoa']
       cm_h_os_cfg=r['cm_data_obj']['cfg']

       d=cm_h_os_cfg
       cm_h_os_c=d.get('cm_classes_uoa',[])
       cm_h_os_p=d.get('cm_properties',{})

    cm_p_c=''
    cm_p_p=''
    if cm_p_uoa!='':
       ii={}
       ii['cm_run_module_uoa']=ini['cfg']['cm_modules']['processor']
       ii['cm_action']='load'
       ii['cm_data_uoa']=cm_p_uoa
       r=cm_kernel.access(ii)
       if r['cm_return']>0: return r

       cm_p_uid=r['cm_uid']
       cm_p_uoa=r['cm_uoa']

       d=r['cm_data_obj']['cfg']

       cm_p_c=d.get('cm_classes_uoa',[])
       cm_p_p=d.get('cm_properties',{})


    # Get list of packages and libraries ***************************************************************************************
    r={}
    r['cm_mixed']=[]

    r1=cm_kernel.access({'cm_run_module_uoa':ini['cm_module_uid'], 'cm_action':'list'})
    if r1['cm_return']>0: cm_kernel.print_for_web('</select><B>cM error:</b> '+r['cm_error']+'<br>')
    for q in r1['cm_mixed']: r['cm_mixed'].append(q)

    for j in ini['cfg']['source_classes_to_install']:
        r1=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['code.source'], 'cm_action':'list', \
                             'cm_classes_uoa':[j]})
        if r1['cm_return']>0: cm_kernel.print_for_web('</select><B>cM error:</b> '+r['cm_error']+'<br>')
        for q in r1['cm_mixed']: 
            if q not in r['cm_mixed']: r['cm_mixed'].append(q)

    if len(r['cm_mixed'])>0:
       pg1=[]

       # List
       for xx in sorted(r['cm_mixed'], key=lambda k: tuple(s.lower() if isinstance(s,str) else s for s in k['cm_display_html'])):
           x=xx['cm_uoa'];  xu=xx['cm_uid'];  xa=xx['cm_alias'];  xd=xx['cm_display_html']
           # Load data
           ii={}
           ii['cm_run_module_uoa']=xx['cm_module_uid']
           ii['cm_action']='load'
           ii['cm_data_uoa']=xu
           r=cm_kernel.access(ii)
           if r['cm_return']==0:
              d=r['cm_data_obj']['cfg']

              add=True

              # Check classes
              dc=d.get('cm_classes_uoa',{})
              if len(dc)>0: xx['cm_classes_uoa']=dc

              # Check overlaping properties from target OS
              dp=d.get('cm_properties',{})
              if len(dp)>0:
                 xx['cm_properties']=dp

                 for q in cm_t_os_p:
                     if q in dp and cm_t_os_p[q]!=dp[q]:
                        add=False
                        break

              # Check dependencies
              if add:
                 dd=d.get('cm_dependencies', {})
                 if len(dd)>0: 
                    xx['cm_dependencies']=dd

                    if 'scenario' in dd and len(dd['scenario'])>0:
                       if len(cm_scen_c)>0:
                          # Class
                          found=False
                          for q in cm_scen_c:
                              if q in dd['scenario']: found=True; break
                          if not found: add=False

                    if 'host_os' in dd and len(dd['host_os'])>0:
                       if len(cm_h_os_c)>0:
                          # Class
                          found=False
                          for q in cm_h_os_c:
                              if q in dd['host_os']: found=True; break
                          if not found: add=False

                    if 'target_os' in dd and len(dd['target_os'])>0:
                       if len(cm_t_os_c)>0:
                          # Class
                          found=False
                          for q in cm_t_os_c:
                              if q in dd['target_os']: found=True; break
                          if not found: add=False

                    if 'target_processor' in dd and len(dd['target_processor'])>0:
                       if len(cm_p_c)>0:
                          # Class
                          found=False
                          for q in cm_p_c:
                              if q in dd['target_processor']: found=True; break

                          if not found: add=False

              if add: pg1.append(xx)

       # Sort by deps *******************************************************************************************
       deps=[]
       pg=[]
       finish=False
       prefinish=False

       while not finish:
          processed=False
          for o in range(0, len(pg1)):
              x=pg1[o]
              if x!={}:
                 to_add=False
                 if 'cm_dependencies' not in x or 'classes' not in x['cm_dependencies']: to_add=True
                 else:
                    if 'classes' in x['cm_dependencies']:
                       found_all=True
                       for qq in x['cm_dependencies']['classes']:
                           if qq not in deps:
                              found_all=False; break
                       if found_all: to_add=True

                       # Check remaining deps
                       if not prefinish:
                          if to_add:
                             for oo1 in range(0, len(pg1)):
                                 if oo1!=o:
                                    oo=pg1[oo1]
                                    if oo!={} and 'cm_classes_uoa' in oo:
                                       deps1=oo['cm_classes_uoa']
                                       failed=False
                                       for qq in x['cm_dependencies']['classes']:
                                           if qq in deps1: 
                                              failed=True; break
                                       if failed: to_add=False

                 if to_add:
                    if 'cm_classes_uoa' in x:
                       for q in x['cm_classes_uoa']: 
                           if q not in deps: deps.append(q)
                    pg.append(x)
                    pg1[o]={}
                    processed=True 

          if not processed: 
             if prefinish: finish=True
             else: prefinish=True
          else:
             pg.append({})

       # Cache all code to check status
       codes={}
       codes_repo={}
       if cm_t_os_uoa!='' and cm_p_uoa!='':
          ii={}
          ii['cm_run_module_uoa']=ini['cfg']['cm_modules']['code']
          ii['cm_action']='list'
          r=cm_kernel.access(ii)
          if r['cm_return']==0:
             for q in r['cm_mixed']:
                 # Load data
                 ii={}
                 ii['cm_run_module_uoa']=ini['cfg']['cm_modules']['code']
                 ii['cm_action']='load'
                 ii['cm_data_uoa']=q['cm_uid']
                 rx=cm_kernel.access(ii)
                 if rx['cm_return']==0:
                    codes[rx['cm_uid']]=rx['cm_data_obj']['cfg']
                    codes_repo[rx['cm_uid']]=rx['cm_repo_uid']

       # Load all classes
       classes={}
       classes_install={}
       classes_install_static={}

       # View  *************************************************************************************************
       line=True; 
       x1=''
       if 'table_bgcolor_line1' in web: x1=' bgcolor="'+web['table_bgcolor_line1']+'" ' 
       x2=''
       if 'table_bgcolor_line2' in web: x2=' bgcolor="'+web['table_bgcolor_line2']+'" '
       x3=''
       if 'table_bgcolor_line3' in web: x3=' bgcolor="'+web['table_bgcolor_line3']+'" ' 
       x4=''
       if 'table_bgcolor_line4' in web: x4=' bgcolor="'+web['table_bgcolor_line4']+'" '

       all_installed_uids=[]

       cm_kernel.print_for_web(web['table_init'])

       cm_kernel.print_for_con('<tr style="background-color:#7F7FFF">')
       cm_kernel.print_for_con('<td><b>Package name:</b></td>')
       cm_kernel.print_for_con('<td><b>Classes:</b></td>')
       cm_kernel.print_for_con('<td><b>Dependencies:</b></td>')
       cm_kernel.print_for_con('<td><b>Install/code UID:</b></td>')
       cm_kernel.print_for_con('<td><b>Install Status:</b></td>')
       cm_kernel.print_for_con('<td><b>Install:</b></td>')
       cm_kernel.print_for_con('</tr>')

       for xx in pg:
           cm_kernel.print_for_con('<tr>')

           if xx!={}:
              x=xx['cm_uoa'];  xu=xx['cm_uid'];  xa=xx['cm_alias'];  xd=xx['cm_display_html'];  xda=xx['cm_display_as_alias']

              # If compiler is selected, remove itself from the list of packages!
              # otherwise had problem with LLVM depending on OpenME
              ign=False
              if xu==a1['compiler_code_uoa']: ign=True

              if True:
                 cc=xx.get('cm_classes_uoa',[])
                 cd=xx.get('cm_dependencies',{}).get('classes',[])

                 cx=[]
                 for c in cc: cx.append(c)
                 for c in cd: cx.append(c)
                 for c in cx:
                     if c not in classes: 
                        #Load class to get name
                        ii={}
                        ii['cm_run_module_uoa']=ini['cfg']['cm_modules']['class']
                        ii['cm_action']='load'
                        ii['cm_data_uoa']=c
                        rx=cm_kernel.access(ii)
                        if rx['cm_return']>0: return rx
                        else: classes[c]=rx
                 if line: 
                    line=False; 
                    if xx['cm_module_uid']==ini['cm_module_uid']: x=x1
                    else: x=x3
                 else: 
                    line=True
                    if xx['cm_module_uid']==ini['cm_module_uid']: x=x2
                    else: x=x4
                 cm_kernel.print_for_con('<tr'+x+'>')

#                 sou=web['http_prefix']+'cm_menu='+web['cm_menu_browse']+'&cm_subaction_view&browse_cid='+xx['cm_module_uid']+':'+xu
                 sou=web['http_prefix']+'view_cid='+xx['cm_module_uid']+':'+xu
                 y='<a href="'+sou+'" target="_blank">'+xd+'</a>'

                 cm_kernel.print_for_web('<td>'+y+'</td>')
                 cm_kernel.print_for_web('<td><small>')
                 first=True; y=''
                 for c in cc:
                     if first: first=False
                     else: y+='<br>'
                     y+=classes[c]['cm_display_html']
                 cm_kernel.print_for_con(y)
                 cm_kernel.print_for_web('</small></td>')


                 cm_kernel.print_for_web('<td><small>')

                 # If not self-reference, print dependences, otherwise show self-reference
                 if ign: 
                    cm_kernel.print_for_web('<B><I>Self-reference, dependencies will not be shown</I></B>')
                 else:
                    failed_deps=False
                    code_deps=[]
                    code_deps1=[]
                    code_deps2=[]
                    compiler_name=''

                    if len(cd)>0:
                       y='<table border="0">'
                       iz=0
                       for c in cd:
                           iz+=1
                           z1='';z2=''

                           if c not in classes_install and c: 
                              z1='<strike>';z2='</strike>'
                              failed_deps=True
                           y+='<tr><td align="left">'+z1+str(iz)+')&nbsp;'+classes[c]['cm_display_as_alias']+z2+'</td>'

                           if c in classes_install: 
                              yy=''
                              name='package_web_install_'+xu+'_'+c
                              value=i.get(name,'')
                              jq=''

                              yz={}
                              if c in classes_install_static: yz=classes_install_static[c]
                              elif c in classes_install: yz=classes_install[c]

                              if c==ini['cfg']['cm_class_compiler']:
#                                 found_compiler=False
#                                 for j in classes_install[c]:
#                                     if a1['compiler_code_uoa']==j['code_uid']:
#                                        jq={'code_uid':a1['compiler_code_uoa']}
#                                        compiler_name=j['name']
#                                        yy='<i>'+compiler_name+'</i>'
#                                        found_compiler=True
#                                        break
#                                 if not found_compiler: failed_deps=True

                                  # FGG removed check for deps here otherwise problem with LLVM 3.2 with OpenME
                                  jq={'code_uid':a1['compiler_code_uoa']}

                                  compiler_name=a1['compiler_code_uoa']

                                  # Load compiler code to get package_uoa
                                  rx=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['code'],
                                                       'cm_action':'load',
                                                       'cm_data_uoa':a1['compiler_code_uoa']})
                                  if rx['cm_return']==0:
                                     compiler_package_uoa=rx['cm_data_obj']['cfg'].get('state_input',{}).get('package_data_uoa','')

                                     if compiler_package_uoa!='':
                                        # Load package
                                        rx=cm_kernel.access({'cm_run_module_uoa':ini['cm_module_uid'],
                                                             'cm_action':'load',
                                                             'cm_data_uoa':compiler_package_uoa})
                                        if rx['cm_return']==0:
                                           compiler_name=rx['cm_data_obj']['cfg'].get('cm_display_as_alias','')
                                           if compiler_name=='': compiler_name=rx['cm_uoa']

                                  yy='<i>'+compiler_name+'</i>'
                              else:
                                 yy='<select name="'+name+'" width="300" style="width: 300px" onchange="document.add_edit.submit();">'

                                 for j in yz:
                                     yyy=''
                                     if value==j['code_uid']: 
                                        jq=j
                                        yyy=' SELECTED '
                                     if yy!='': yy+=','

                                     yy+='<option value="'+j['code_uid']+'"'+yyy+'>'+j['name']+'</option>'
                                 yy+='</select>'
                              y+='<td>'+yy+'</td></tr>'

                              if jq=='' and len(yz)>0: jq=yz[0]

                              if jq!='':
                                 code_deps_var=classes[c]['cm_data_obj']['cfg'].get('code_deps_var','')
                                 if code_deps_var!='': 
                                    code_deps.append({code_deps_var:jq['code_uid']})
                                    code_deps1.append({c:jq['code_uid']})
                                    if c!=ini['cfg']['cm_class_compiler']:
                                       code_deps2.append({c:jq['code_uid']})
                       y+='</table>'
                       cm_kernel.print_for_con(y)

                    cm_kernel.print_for_web('</small></td>')

                 # Check status and deps ************************************************************************
                 found=False
                 y=''
                 z=''
                 if not failed_deps and cm_t_os_uoa!='' and cm_p_uoa!='':
                    qr=''
                    for q in codes:
                        qq=codes[q]

                        qqd=qq.get('cm_source_data_uoa','')
                        qqm=qq.get('cm_source_module_uoa','')

                        success=False
                        if qq.get('build_finished_successfully','')=='yes': success=True

                        # Check package/source code
                        if (qqd!=xu or qqm!=xx['cm_module_uid']):
                           continue

                        add=True
                        if xx['cm_module_uid']==ini['cm_module_uid']:

                           si=qq.get('state_input',{})
                           qqp=si.get('run_target_processor_uoa','')
                           qqbtos=si.get('build_target_os_uoa','')
                           qqwd=si.get('package_data_uoa','')
                           if qqwd=='': qqwd=si.get('work_dir_data_uoa','')

                           # for packages, we use comparison by class (less restrictive) to reuse packages for different setups
                           dd=qq
                           if 'host_os' in dd:
                              # Prune by target OS
                              if len(cm_h_os_c)>0:
                                 # Class
                                 found=False
                                 for q in cm_h_os_c:
                                     if q in dd['host_os']: found=True; break
                                 if not found: add=False
                           if not add: continue

                           if 'target_os' in dd:
                              # Prune by target OS
                              if len(cm_t_os_c)>0:
                                 # Class
                                 found=False
                                 for q in cm_t_os_c:
                                     if q in dd['target_os']: found=True; break
                                 if not found: add=False
                           if not add: continue

                           if 'target_processor' in dd:
                              # Prune by target OS
                              if len(cm_p_c)>0:
                                 # Class
                                 found=False
                                 for q in cm_p_c:
                                     if q in dd['target_processor']: found=True; break
                                 if not found: add=False
                           if not add: continue
                        else:
                           # Check deps **************************************************************************************
                           # for libraries, we use exact comparison by UID for a given setup
                           add=False

                           rdep=qq.get('cm_dependencies_real',{})

                           if rdep.get('host_os','')!='' and rdep['host_os']!=cm_h_os_uid: continue
                           if rdep.get('target_os','')!='' and rdep['target_os']!=cm_t_os_uid: continue
                           if rdep.get('target_processor','')!='' and rdep['target_processor']!=cm_p_uid: continue

                           add=True
                           j=rdep.get('classes',{})
                           for t in j:
                               t1=t.keys()[0]
                               t2=t[t1]
                               found=False
                               for e in code_deps1:
                                   e1=e.keys()[0]
                                   e2=e[e1]
                                   if e1==t1 and e2==t2: found=True; break
                               if not found:
                                  add=False
                                  break

                           if not add: continue

                           if rdep.get('compilation_type','')!='' and a1.get('compilation_type','')!=rdep['compilation_type']:
                              add=False
                              found=False
                              continue

                           if rdep.get('compilation_type','')=='static':
                              qxd=qq.get('cm_display_as_alias','')
                              if qxd=='': qxd=xd
                              for j in cc:
                                  if j not in classes_install_static: 
                                        classes_install_static[j]=[{'code_uid':q, 'name':qxd}]
                                  else:
                                     if q not in classes_install_static[j]: 
                                        classes_install_static[j].append({'code_uid':q, 'name':qxd})

                        if add: qr=q

                    if qr!='':
                       sou=web['http_prefix']+'cm_menu='+web['cm_menu_browse']+'&cm_subaction_view&browse_cid='+ini['cfg']['cm_modules']['code']+':'+qr
                       y='<a href="'+sou+'" target="_blank">'+qr+'</a>'
                       qq=codes[qr]
                       all_installed_uids.append(qr)

                       success=False
                       if qq.get('build_finished_successfully','')=='yes': success=True

                       if success:
                          z='<span style="color:#00009F"><b>Success</b></span>'
                          qxd=qq.get('cm_display_as_alias','')
                          if qxd=='': qxd=xd
                          for j in cc:
                              if j not in classes_install: 
                                 classes_install[j]=[{'code_uid':qr, 'name':qxd}]
                              else:
                                 if qr not in classes_install[j]: classes_install[j].append({'code_uid':qr, 'name':qxd})

                       else: 
                          z='<span style="color:#9F0000"><b>Not finished<BR>(either in progress or error)</b></span>'

                       found=True

                 cm_kernel.print_for_web('<td><small>'+y+'</small></td>')
                 cm_kernel.print_for_web('<td align="center"><small>'+z+'</small></td>')

                 z=''
                 y=''
                 if not failed_deps and cm_t_os_uoa!='' and cm_p_uoa!='' and not ign:
                    # Check if enough params for an install button
                    cm_json={}
                    rem=[]
                    rm=cm_h_os_cfg.get('rem','')

                    # Load package or source-code to check default build script
                    ii={}
                    ii['cm_run_module_uoa']=xx['cm_module_uid']
                    ii['cm_action']='load'
                    ii['cm_data_uoa']=xx['cm_uid']
                    rx=cm_kernel.access(ii)
                    if rx['cm_return']>0: return rx
                    d1=rx['cm_data_obj']['cfg']

                    if xx['cm_module_uid']==ini['cm_module_uid']:
                       rem.append(rm+' package: '+str(xd))
                       cm_json['install_data_display_as_alias']=str(xd)
                       y1='Install'
                       if not failed_deps and cm_t_os_uoa!='' and cm_h_os_uoa!='' and cm_p_uoa!='':
                          z=web['http_prefix']+'cm_web_module_uoa=package&cm_web_action=install&package_data_uoa='+xu+\
                            '&package_host_os_uoa='+cm_h_os_uoa+'&build_target_os_uoa='+cm_t_os_uoa+\
                            '&run_target_processor_uoa='+cm_p_uoa+'&cm_detach_console=yes'
                          if found:
                            z+='&install_data_uid='+qr+'&install_repo_uoa='+codes_repo[qr]
                            y1='Re-install'
                          elif cm_repo_uoa!='': 
                            z+='&install_repo_uoa='+cm_repo_uoa
                    else:
                       rem.append(rm+' package: '+str(xd)+' - '+compiler_name+' - '+a1.get('compilation_type',''))
                       cm_json['install_data_display_as_alias']=str(xd)+' - '+compiler_name+' - '+a1.get('compilation_type','')
                       y1='Build'
                       if not failed_deps and cm_t_os_uoa!='' and cm_h_os_uoa!='' and cm_p_uoa!='':
                          z=web['http_prefix']+'cm_menu=scenarios&cm_submenu=ctuning_code_source_build'

                          cm_json['#form1##run_host_os_uoa']=cm_h_os_uoa
                          cm_json['#form1##build_target_os_uoa']=cm_t_os_uoa
                          cm_json['#form1##run_target_processor_uoa']=cm_p_uoa
                          cm_json['#form1##work_dir_data_uoa']=xu
                          cm_json['#form1##work_dir_repo_uoa']=''
                          cm_json['#form1##install']='yes'
                          if 'ctuning_setup_uoa' in a1: cm_json['#form1##ctuning_setup_uoa']=a1['ctuning_setup_uoa']
                          if 'package_repo_uoa' in a1: cm_json['#form1##install_repo_uoa']=a1['package_repo_uoa']
                          cross_build_static_lib=False
                          if 'compiler_code_uoa' in a1: 
                             cm_json['#form1##compiler_code_uoa']=a1['compiler_code_uoa']

                             # Load compiler code to check if cross-compile
                             rx=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['code'],
                                                  'cm_action':'load',
                                                  'cm_data_uoa':a1['compiler_code_uoa']})
                             if rx['cm_return']==0: 
                                drx=rx['cm_data_obj']['cfg']
                                if drx.get('build_params',{}).get('cross_build_static_lib','')=='yes': 
                                   cross_build_static_lib=True

                          if 'compilation_type' in a1: cm_json['#form1##compilation_type']=a1['compilation_type']

                          # Always force dependencies even if empty
                          cm_json['#form1##cm_dependencies']=code_deps2

                          if found:
                            y1='Re-build'
                            cm_json['#form1##install_data_uid']=qr

                          if 'build_scripts_uoa' in d1:
                             cm_json['#form1##build_run_script_uoa']=d1['build_scripts_uoa'][0]

                          if cross_build_static_lib and 'build_scripts_names' in d1:
                             for j in d1['build_scripts_names']:
                                 for jj in d1['build_scripts_names'][j]:
                                     if 'cross_build_static_lib' in jj:
                                        cm_json['#form1##build_run_script']=jj
                                        break

                    cm_json['add_rem_to_script']=rem

                    cm_json['code_deps']=code_deps

                    if 'keep_all_files' in a1 and a1['keep_all_files']!='': cm_json['keep_all_files']=a1['keep_all_files']

                    if 'skip_extract_and_build' in a1: cm_json['skip_extract_and_build']=a1['skip_extract_and_build']
                    if 'number_of_parallel_jobs_for_build' in a1: 
                       cm_json['run_set_env2']={}
                       cm_json['run_set_env2']['CM_PARALLEL_JOB_NUMBER']=a1['number_of_parallel_jobs_for_build']

                    package_info={}
                    if 'cm_classes_uoa' in xx: package_info['cm_classes_uoa']=xx['cm_classes_uoa']
                    if 'cm_properties' in xx: package_info['cm_properties']=xx['cm_properties']
                    if 'cm_dependencies' in xx: package_info['cm_dependencies']=xx['cm_dependencies']

                    package_info['cm_source_data_uoa']=xu
                    package_info['cm_source_module_uoa']=xx['cm_module_uid']

                    # Prepare real dependencies

                    package_info['cm_dependencies_real']={}

                    package_info['cm_dependencies_real']['classes']=code_deps1

                    dd=d1.get('cm_dependencies',{})
                    if 'host_os' in dd:          package_info['cm_dependencies_real']['host_os']=cm_h_os_uid
                    if 'target_os' in dd:        package_info['cm_dependencies_real']['target_os']=cm_t_os_uid
                    if 'target_processor' in dd: package_info['cm_dependencies_real']['target_processor']=cm_p_uid

                    # Check if package requires compilation, and then record compiler and compilation type
                    if 'classes' in dd and ini['cfg']['cm_classes']['compiler'] in dd['classes']:
                       if 'compiler_code_uoa' in a1:
                          package_info['cm_dependencies_real']['compiler_code_uoa']=a1['compiler_code_uoa']
                       if 'compilation_type' in a1:
                          package_info['cm_dependencies_real']['compilation_type']=a1['compilation_type']

                    cm_json['add_to_code_entry']=package_info

                    rx=cm_kernel.convert_cm_array_to_uri({'cm_array':cm_json})
                    if rx['cm_return']>0: return rx

                    z+='&cm_json='+rx['cm_string']

                    y='<a href="'+z+'" target="_blank">'+y1+'</a>'

                 cm_kernel.print_for_web('<td align="center"><small>'+y+'</small></td>')

           else:
              cm_kernel.print_for_con('<td colspan=6><HR class="cm-hr"></td>')

           cm_kernel.print_for_con('</tr>')

       cm_kernel.print_for_con('</table>')

       cm_kernel.print_for_con('<small><B>All installed UIDs:</B><BR><i>')
       for q in all_installed_uids:
           cm_kernel.print_for_con(' '+q)
       cm_kernel.print_for_con('</i></small><BR>')


    cm_kernel.print_for_con('<input type="submit" class="cm-button" value="Refresh">')

    cm_kernel.print_for_con('</FORM>')

    return {'cm_return':0}

# ============================================================================
def installed(i):

    """
    List installed packages

    Input:  {
              (code_repo_uoa)             - repo UOA to list code
              (prune_by_class_uoa)        - prune by 1 class UOA
              (prune_by_name)             - prune by name (checks for inclusion; case insensitive)
              (fuzzy_match)               - if 'yes', check inclusion of 'prune_by_name' in name, otherwise exact match
              (prune_by_name_uoa)         - prune by name UOA
              (prune_by_type)             - prune by "library_or_plugin" or "package"
              (prune_by_host_os)          - prune by host os
              (prune_by_target_os)        - prune by target os
              (prune_by_target_processor) - prune by target processor
              (prune_by_compiler)         - if library or plugin, prune by compiler
              (prune_by_os_from_kernel)   - if 'yes', take OS from kernel
              (only_uoa)                  - return only UOA
            }

    Output: {
              cm_return - return code = 0, if successful
              final     - list with code entries in cM 'list' format
            }
    """

    # Checking some pruning parameters
    pbcu=i.get('prune_by_class_uoa','')
    pbn=i.get('prune_by_name','').lower()
    fm=i.get('fuzzy_match','')
    pbnu=i.get('prune_by_name_uoa','')
    pbt=i.get('prune_by_type','').lower()
    pbho=i.get('prune_by_host_os','').lower()
    pbto=i.get('prune_by_target_os','').lower()
    pbtp=i.get('prune_by_target_processor','').lower()
    pbc=i.get('prune_by_compiler','').lower()

    ou=i.get('only_uoa','')

    pik=i.get('prune_by_os_from_kernel','')
    if pik!='':
       dos=cm_kernel.ini['dcfg'].get('cm_default_os_uoa','')
       r=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['os'], 'cm_action':'load', 'cm_data_uoa':dos})
       if r['cm_return']>0: return r
       if r['cm_alias']!='': dos=r['cm_alias']

       pbho=dos
       pbto=dos

    ii={'cm_run_module_uoa':ini['cfg']['cm_modules']['code'],
        'cm_action':'list',
       }
    if i.get('code_repo_uoa','')!='': ii['cm_repo_uoa']=i['code_repo_uoa']
    r=cm_kernel.access(ii)
    if r['cm_return']>0: return r

    m=r['cm_mixed']
    ms=sorted(m, key=lambda k: k['cm_display_as_alias'])

    final=[]
    for q in ms:
        d=q['cm_data_obj_cfg']
        bfs=d.get('build_finished_successfully','')
        cl=d.get('cm_classes_uoa',[])

        show=True
        if pbcu!='' and pbcu not in cl:
           show=False

        if show:
           if bfs=='' or bfs=='yes':
              si=d.get('state_input',{})
              pack=si.get('package_data_uoa','')
              source=si.get('work_dir_data_uoa','')

              show=True
              if pbnu!='' and not (pbnu==pack or pbnu==source):
                 show=False

              if show:
                 if pack!='' or source!='':
                    xcompiler=''
                    if pack=='':
                       # If library/plugin **************
                       lib=True
                       t='library/plugin'
                       t1='library_or_plugin'

                       r=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['code.source'], 'cm_action':'load', 'cm_data_uoa':source})
                       if r['cm_return']==0:
                          name=r.get('cm_display_as_alias',source) 

                          cc_uoa=d.get('cm_dependencies_real',{}).get('compiler_code_uoa','')
                          r=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['code'], 'cm_action':'load', 'cm_data_uoa':cc_uoa})
                          if r['cm_return']==0: 
                             cp_uoa=r['cm_data_obj']['cfg'].get('state_input',{}).get('package_data_uoa','')

                             if cp_uoa!='':
                                r=cm_kernel.access({'cm_run_module_uoa':ini['cm_module_uid'], 'cm_action':'load', 'cm_data_uoa':cp_uoa})
                                if r['cm_return']==0: 
                                   xcompiler='"'+r.get('cm_display_as_alias',cp_uoa)+'"'
                    else:
                       # If package **************
                       lib=False
                       t='package'
                       t1=t
                       r=cm_kernel.access({'cm_run_module_uoa':ini['cm_module_uid'], 'cm_action':'load', 'cm_data_uoa':pack})
                       if r['cm_return']==0: 
                          name=r.get('cm_display_as_alias',pack) 

                    show=True

                    if pbt!='' and pbt!=t1:
                       show=False
                    elif pbn!='':
                         if fm=='yes' and not pbn in name.lower(): #re.match(pbn,name.lower())):
                             show=False
                         elif pbn!='' and fm!='yes' and pbn!=name.lower(): #re.match(pbn,name.lower())):
                             show=False
                    elif t=='library/plugin' and pbc!='':
                         if fm=='yes' and not pbc in xcompiler.lower():
                            show=False
                         elif fm!='yes' and pbc!=xcompiler.lower():
                            show=False

                    if show:
                       st='%14s' % t

                       cm_uoa=q['cm_uoa']
                       cm_uid=q['cm_uid']
                       daa=q.get('cm_display_as_alias','')

                       # Get host OS
                       ho=si.get('run_host_os_uoa','')
                       xho=ho
                       xho1=ho
                       r=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['os'], 'cm_action':'load', 'cm_data_uoa':ho})
                       if r['cm_return']>0: return r
                       if r['cm_alias']!='': 
                          xho=r['cm_alias']
                          xho1=r['cm_uid']

                       # Get target OS
                       to=si.get('build_target_os_uoa','')
                       xto=to
                       xto1=to
                       r=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['os'], 'cm_action':'load', 'cm_data_uoa':to})
                       if r['cm_return']>0: return r
                       if r['cm_alias']!='': 
                          xto=r['cm_alias']
                          xto1=r['cm_uid']

                       # Get target processor
                       tp=si.get('run_target_processor_uoa','')
                       xtp=tp
                       xtp1=tp
                       r=cm_kernel.access({'cm_run_module_uoa':ini['cfg']['cm_modules']['processor'], 'cm_action':'load', 'cm_data_uoa':tp})
                       if r['cm_return']>0: return r
                       if r['cm_alias']!='': 
                          xtp=r['cm_alias']
                          xtp1=r['cm_uid']

                       sto='%25s' % xto
                       stp='%16s' % xtp
                       sho='%25s' % xho

                       show=True

                       if pbho!='' and pbho!=xho and pbho!=xho1:
                          show=False
                       elif pbto!='' and pbto!=xto and pbto!=xto1:
                          show=False
                       elif pbtp!='' and pbtp!=xtp and pbtp!=xtp1:
                          show=False

                       if show:
                          final.append(q)
                          if i.get('cm_console','')=='txt':
                             if ou=='':
                                cm_kernel.print_for_con(cm_uoa+' '+st+' '+sho+' '+sto+' '+stp+'  "'+name+'"'+'   '+xcompiler)
                                cm_kernel.print_for_con('')
                             else:
                                cm_kernel.print_for_con(cm_uoa)

    return {'cm_return':0, 'final':final}
