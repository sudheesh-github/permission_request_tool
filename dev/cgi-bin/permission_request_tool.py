#!/usr/bin/python

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import yaml
import os
from datetime import date, datetime
import logging
import time
import json
from unidecode import unidecode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'e5ac358c-f0bf-11e5-9e39-d3b532c10a28'

dir_path = os.path.dirname(os.path.realpath(__file__))
cfgfile = dir_path + '/../etc/config/main.cfg'

today = str(datetime.strftime(date.today(), '%Y_%m_%d'))

with open(cfgfile, 'r') as f:
    cfgobj = yaml.load(f)

hst = cfgobj["Main"]["hst"]
prt = cfgobj["Main"]["prt"]
lck_fil_cntr = int(cfgobj["Main"]["lockfile_check_counter"])

admin_temp_file = cfgobj["Mail"]["admin_template_file"]

lck_file_wait_time = int(cfgobj["Main"]["lockfile_wait_time"])

scriptname = os.path.basename(__file__).split(".")[0]

logfilenam = dir_path + '/../logs/' + scriptname + '_' + today + '.log'
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)
ch = logging.FileHandler(logfilenam)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')
ch.setFormatter(formatter)
logger.addHandler(ch)


def send_email(SUBJECT, BODY, TO, FROM):
    relay_host = cfgobj["Mail"]["relay_host"]
    MESSAGE = MIMEMultipart('alternative')
    MESSAGE['subject'] = SUBJECT
    MESSAGE['To'] = TO
    MESSAGE['From'] = FROM
    rcpt = TO
    HTML_BODY = MIMEText(BODY, 'html')
    MESSAGE.attach(HTML_BODY)
    server = smtplib.SMTP(relay_host)
    server.sendmail(FROM, rcpt.split(','), MESSAGE.as_string())
    server.quit()


#this function is called it the url ends with home i.e. the front page where user initially logs in
@app.route('/home')
def home():
    #Going to extract User email address
    user = request.headers.get('X-WEBAUTH-LNXUSER')
    #Setting the email id of the user ins session so that can be used till session is active
    session['email'] = user.split('@')[0].lower() + '@shell.com'
    return render_template('index.html', host = hst, port = prt, email = session.get('email'))

#This function is called when user submits the request from the GUI.
#This function cannot be called directly as it only accepts POST and GET method.

@app.route('/tcspath', methods = ['POST', 'GET'])
def tcs_path():
    requestor = session.get('email')
    main_dir_path = cfgobj["Main"]["files_dir_path"]
    envrnmnt = cfgobj["Main"]["environment"]
    foldr = cfgobj["Main"]["toprocessfolder"]
    check_countr = 0
    lock_check_countr = 0
    pathtype = request.form['pathtype']
    path = request.form['path']
    admin_mail_val = {}
    data = {}
    admin_temp_val = {}
    fromaddr = cfgobj["Mail"]["mail_from"]
    data['path'] = []
    logger.info("Requestor:%s PathType:%s Path:%s",requestor,pathtype,path)
    msg = cfgobj["Message"]["req_submission_success"]
    if (pathtype == 'ifspath'):
        path_list = path.split('/')
        if (len(path_list) > 8):
            if (path_list[1] == 'ifs' and path_list[2] in cfgobj["Main"]["regions"] and path_list[3] in cfgobj["Main"]["regions"][path_list[2]] and path_list[4] in cfgobj["Main"]["level3struct"]):
                site = path_list[3]
                path_name = ''
                file_name = requestor + '.csv'
                tmp_file_name = requestor + '.csv.tmp'
                path_file_name = main_dir_path + site + '/' + envrnmnt + "/" + foldr + "/" + file_name
                tmp_path_file_name = main_dir_path + site + '/' + envrnmnt + "/" + foldr + "/" + tmp_file_name
                logger.info("File to be created in toprocess folder : %s", path_file_name)
                lockfile = path_file_name + '.lck'
                if (os.path.isfile(path_file_name)):
                    if (os.path.isfile(lockfile)):
                        logger.info("Lock File exists:%s",lockfile)
                        logger.info("Going to write in temporary file %s", tmp_path_file_name)
                        with open(tmp_path_file_name, 'w') as t:
                            logger.info("File %s opened for writing", tmp_path_file_name)
                            data['path'].append({
                                'Path': path,
                                'DFS Path': 'NA',
                                'Requestor': requestor
                            })
                            json.dump(data, t)
                            logger.info("Writing to temporary file %s completed", tmp_path_file_name)
                        logger.info("Going to check whether lock file %s is deleted by cluster script or not",lockfile)
                        while (check_countr < lck_fil_cntr and os.path.isfile(lockfile)):
                            check_countr = check_countr + 1
                            logger.info("Check counter: %s", str(check_countr))
                            logger.info("Going to sleep for %s", str(lck_file_wait_time))
                            time.sleep(lck_file_wait_time)
                        if (os.path.isfile(lockfile)):
                            logger.info("Lock file created by cluster script is not removed. %s", lockfile)
                            msg = cfgobj["Message"]["cluster_script_lock_file_exists"]
                            logger.info("Going to send email to admins as the lock file %s generated by cluster script is not deleted", lockfile)
                            admin_temp_val['files'] = lockfile
                            admin_temp_val['sender_mail'] = fromaddr
                            html = render_template(admin_temp_file, val=admin_temp_val)
                            send_email(cfgobj["Message"]["lock_file_issue_subject"], html, cfgobj["Mail"]["admin_mail"], fromaddr)
                        else:
                            logger.info("Going to rename the temporary file %s to original filename %s", tmp_path_file_name, path_file_name)
                            os.rename(tmp_path_file_name, path_file_name)
                            if (os.path.isfile(tmp_path_file_name)):
                                logger.info("Temporary file %s renaming failed", tmp_path_file_name)
                            else:
                                logger.info("Temposrary file %s renamed", tmp_path_file_name)

#                             open(lockfile, 'a').close()
#                             logger.info("Lock file %s created", lockfile)
#                             with open(path_file_name, 'w') as f:
#                                 logger.info("File %s opened for writing", path_file_name)
#                                 data['path'].append({
#                                     'Path': path,
#                                     'DFS Path': 'NA',
#                                     'Requestor': requestor
#                                 })
#                                 json.dump(data, f)
#                                 logger.info("Writing to file %s completed", path_file_name)

                    else:
                        logger.info("Lock file %s does not exist", lockfile)
                        #open(lockfile, 'a').close()
                        with open(path_file_name, 'r') as fil:
                            #val = fil.readlines()
                            val = json.load(fil)
                        cur_path_lst = []
                        for v in val['path']:
                            cur_path_lst.append(v['path'])
                        if path not in cur_path_lst:
                            logger.info("Opening the file %s to append path %s", path_file_name, path)
                            with open(path_file_name, 'r') as f:
                                val = json.load(f)
                            val['path'].append({
                                'Path': path,
                                'DFS Path': 'NA',
                                'Requestor': requestor
                                })
                            with open(path_file_name, 'w') as f:
                                json.dump(val,f)
                        else:
                            logger.info("Path %s already exists in the file %s", path, path_file_name)
                            msg = cfgobj["Message"]["duplicate_request"]
#                         if (os.path.isfile(lockfile)):
#                             try:
#                                 os.remove(lockfile)
#                                 logger.info("lock file removed successfully %s", lockfile)
#                             except Exception as e:
#                                 logger.info("Got error while deleting lock file : %s", lockfile)
#                                 send_email()
                else:
                    #open(lockfile, 'a').close()
                    #logger.info("Lock file %s is created", lockfile)
                    with open(path_file_name, 'w') as f:
                        logger.info("File %s created", path_file_name)
                        data['path'].append({
                                'Path': path,
                                'DFS Path': 'NA',
                                'Requestor': requestor
                            })
                        json.dump(data, f)
                        logger.info("Writing to file %s completed", path_file_name)
#                     if (os.path.isfile(lockfile)):
#                         try:
#                             os.remove(lockfile)
#                             while (lock_check_countr < 3):
#                                 lock_check_countr = lock_check_countr + 1
#                                 if (os.path.isfile(lockfile)):
#                                     os.remove(lockfile)
#                                 else:
#                                     logger.info("lock file removed successfully %s", lockfile)
#                                     break
#                         except Exception as e:
#                             logger.info("Got error while deleting lock file : %s", lockfile)
#                             send_email()


            else:
                msg = cfgobj["Message"]["incorrect_path"]
        elif (len(path_list) > 6):
            if (path_list[1] == 'ifs' and path_list[2] in cfgobj["Main"]["regions"] and path_list[3] in cfgobj["Main"]["regions"][path_list[2]] and path_list[4] in cfgobj["Main"]["level3struct"] and path_list[5] == 'apps'):
                site = path_list[3]
                path_name = ''
                file_name = requestor + '.csv'
                path_file_name = main_dir_path + site + '/' + envrnmnt + "/" + foldr + "/" + file_name
                logger.info("File to be created in toprocess folder : %s", path_file_name)
                lockfile = path_file_name + '.lck'
                if (os.path.isfile(path_file_name)):
                    if (os.path.isfile(lockfile)):
                        logger.info("Lock File exists:%s",lockfile)
                        logger.info("Going to write in temporary file %s", tmp_path_file_name)
                        with open(tmp_path_file_name, 'w') as t:
                            logger.info("File %s opened for writing", tmp_path_file_name)
                            data['path'].append({
                                'Path': path,
                                'DFS Path': 'NA',
                                'Requestor': requestor
                            })
                            json.dump(data, t)
                            logger.info("Writing to temporary file %s completed", tmp_path_file_name)
                        logger.info("Going to check whether lock file %s is deleted by cluster script or not",lockfile)
                        while (check_countr < lck_fil_cntr and os.path.isfile(lockfile)):
                            check_countr = check_countr + 1
                            logger.info("Check counter: %s", str(check_countr))
                            logger.info("Going to sleep for %s", str(lck_file_wait_time))
                            time.sleep(lck_file_wait_time)
                        if (os.path.isfile(lockfile)):
                            logger.info("Lock file created by cluster script is not removed. %s", lockfile)
                            msg = cfgobj["Message"]["cluster_script_lock_file_exists"]
                            logger.info("Going to send email to admins as the lock file %s generated by cluster script is not deleted", lockfile)
                            admin_temp_val['files'] = lockfile
                            admin_temp_val['sender_mail'] = fromaddr
                            html = render_template(admin_temp_file, val=admin_temp_val)
                            send_email(cfgobj["Message"]["lock_file_issue_subject"], html, cfgobj["Mail"]["admin_mail"], fromaddr)
                        else:
                            logger.info("Going to rename the temporary file %s to original filename %s", tmp_path_file_name, path_file_name)
                            os.rename(tmp_path_file_name, path_file_name)
                            if (os.path.isfile(tmp_path_file_name)):
                                logger.info("Temporary file %s renaming failed", tmp_path_file_name)
                            else:
                                logger.info("Temporary file %s renamed", tmp_path_file_name)
#                             open(lockfile, 'a').close()
#                             logger.info("Lock file %s created", lockfile)
#                             with open(path_file_name, 'w') as f:
#                                 logger.info("File %s opened for writing", path_file_name)
#                                 data['path'].append({
#                                     'Path': path,
#                                     'DFS Path': 'NA',
#                                     'Requestor': requestor
#                                     })
#                                 json.dump(data, f)
#                                 logger.info("Writing to file %s completed", path_file_name)
#                             if (os.path.isfile(lockfile)):
#                                 try:
#                                     os.remove(lockfile)
#                                     logger.info("lock file removed successfully %s", lockfile)
#                                 except Exception as e:
#                                     logger.info("Got error while deleting lock file : %s", lockfile)
#                                     send_email()
                    else:
                        logger.info("Lock file %s does not exist", lockfile)
                        #open(lockfile, 'a').close()
                        with open(path_file_name, 'r') as fil:
                            val = json.load(fil)
                        cur_path_lst = []
                        for v in val['path']:
                            cur_path_lst.append(v['Path'])
                        if path not in cur_path_lst:
                            logger.info("Opening the file %s to append path %s", path_file_name, path)
                            val['path'].append({
                                'Path': path,
                                'DFS Path': 'NA',
                                'Requestor': requestor
                                })
                            with open(path_file_name, 'w') as f:
                                json.dump(val, f)
                        else:
                            logger.info("Path %s already exists in the file %s", path, path_file_name)
                            msg = cfgobj["Message"]["duplicate_request"]
#                         if (os.path.isfile(lockfile)):
#                             try:
#                                 os.remove(lockfile)
#                                 while (lock_check_countr < 3):
#                                     lock_check_countr = lock_check_countr + 1
#                                     if (os.path.isfile(lockfile)):
#                                         os.remove(lockfile)
#                                     else:
#                                         logger.info("lock file removed successfully %s", lockfile)
#                                         break
#                             except Exception as e:
#                                 logger.info("Got error while deleting lock file : %s", lockfile)
#                                 send_email()
                else:
                    #open(lockfile, 'a').close()
                    #logger.info("Lock file %s is created", lockfile)
                    with open(path_file_name, 'w') as f:
                        logger.info("File %s created", path_file_name)
                        data['path'].append({
                            'Path': path,
                            'DFS Path': 'NA',
                            'Requestor': requestor
                            })
                        json.dump(data, f)
                        logger.info("Writing to file %s completed", path_file_name)
#                     if (os.path.isfile(lockfile)):
#                         try:
#                             os.remove(lockfile)
#                             while (lock_check_countr < 3):
#                                 lock_check_countr = lock_check_countr + 1
#                                 if (os.path.isfile(lockfile)):
#                                     os.remove(lockfile)
#                                 else:
#                                     logger.info("lock file removed successfully %s", lockfile)
#                                     break
#                         except Exception as e:
#                             logger.info("Got error while deleting lock file : %s", lockfile)
#                             send_email()
            else:
                msg = cfgobj["Message"]["incorrect_path"]

        else:
            msg = cfgobj["Message"]["path_above_l7"]
##
## This marks the section in which DFS paths are being processed        
##
    if (pathtype == "dfspath"):
        f = open("/tmp/file", 'w+')
        path_r = repr(path)                                     ## changed the name from path_raw to path_r
        path_raw = path_r.replace('\\xa0', ' ')                 ## added new line
        ignore_l3 = cfgobj["Main"]["level3struct"].split(',')
        logger.info("Path is dfs")
        logger.info("DFS path is %s", path_raw)
        path_list_raw = path_raw.split("\\")
        path_list = []
        for i in path_list_raw:
            if (i != ''):
                if ("'" in i):
                    path_list.append(i[:-1])
                else:
                    path_list.append(i)

        if (path_list[2].lower() == 'tcs'):
            if (path_list[1] in cfgobj["Main"]["dfsregions"]):
                if (path_list[3] in cfgobj["Main"]["dfsregions"][path_list[1]]):
                    if (path_list[1].lower() == 'americas.shell.com'):
                        rgn_path = 'ifs/am/'
                    elif (path_list[1].lower() == 'europe.shell.com'):
                        rgn_path = 'ifs/eu/'
                    else:
                        rgn_path = 'ifs/ap/'

                    locn_path = rgn_path + str(path_list[3]) + "/"
                    logger.info("Location Path %s: ", locn_path)
                    if ('nobackup' in path_list[5]):
                        fnl_path = locn_path + 'nobackup/'
                    elif ('scratch' in path_list[5]):
                        fnl_path = locn_path + 'scratch/'
                    else:
                        fnl_path = locn_path + 'backup/'

                    for i in range(4,len(path_list)):
                        if ('.' in path_list[i]):
                            pth = path_list[i].split('.')
                            for j in pth:
                                if (j not in ignore_l3):
                                    if (len(fnl_path.split('/')) > 7):
                                        fnl_path = fnl_path + j + "/"
                                    else:
                                        fnl_path = fnl_path + j.lower() + "/"
                        else:
                            if (len(fnl_path.split('/')) > 7):
                                fnl_path = fnl_path + path_list[i] + "/"
                            else:
                                fnl_path = fnl_path + path_list[i].lower() + "/"

                    fnl_path = fnl_path[:-1]
                    dfs_site = path_list[3]
                    dfs_path_file_name = main_dir_path + dfs_site + '/' + envrnmnt + "/" + foldr + "/" + requestor + ".csv"
                    tmp_dfs_path_file_name = main_dir_path + dfs_site + '/' + envrnmnt + "/" + foldr + "/" + requestor + ".csv.tmp"
                    dfslockfile = dfs_path_file_name + '.lck'
                    dfs_to_ifs_path = '/' + fnl_path
                    if (len(dfs_to_ifs_path.split('/')) > 8):
                        if (os.path.isfile(dfs_path_file_name)):
                            logger.info("File %s exists", dfs_path_file_name)
                            if (os.path.isfile(dfslockfile)):
                                logger.info("Lock File exists:%s",dfslockfile)
                                logger.info("Going to write in temporary file %s", tmp_dfs_path_file_name)
                                with open(tmp_dfs_path_file_name, 'w') as t:
                                    logger.info("File %s opened for writing", tmp_dfs_path_file_name)
                                    data['path'].append({
                                        'Path': dfs_to_ifs_path,
                                        'DFS Path': path_raw,
                                        'Requestor': requestor
                                    })
                                    json.dump(data, t)
                                    logger.info("Writing to temporary file %s completed", tmp_dfs_path_file_name)
                                logger.info("Going to check whether lock file %s is deleted by cluster script or not",dfslockfile)
                                while (check_countr < lck_fil_cntr and os.path.isfile(dfslockfile)):
                                    check_countr = check_countr + 1
                                    logger.info("Check counter: %s", str(check_countr))
                                    logger.info("Going to sleep for %s", str(lck_file_wait_time))
                                    time.sleep(lck_file_wait_time)
                                if (os.path.isfile(dfslockfile)):
                                    logger.info("Lock file %s exists. Cannot process the request", dfslockfile)
                                    msg = cfgobj["Message"]["cluster_script_lock_file_exists"]
                                    logger.info("Going to send email to admins as the lock file %s generated by cluster script is not deleted", lockfile)
                                    admin_temp_val['files'] = dfslockfile
                                    admin_temp_val['sender_mail'] = fromaddr
                                    html = render_template(admin_temp_file, val=admin_temp_val)
                                    send_email(cfgobj["Message"]["lock_file_issue_subject"], html, cfgobj["Mail"]["admin_mail"], fromaddr)
                                else:
                                    logger.info("Going to rename the temporary file %s to original filename %s", tmp_dfs_path_file_name, dfs_path_file_name)
                                    os.rename(tmp_dfs_path_file_name, dfs_path_file_name)
                                    if (os.path.isfile(tmp_dfs_path_file_name)):
                                        logger.info("Temporary file %s renaming failed", tmp_dfs_path_file_name)
                                    else:
                                        logger.info("Temporary file %s renamed", tmp_dfs_path_file_name)
#                                     open(dfslockfile, 'a').close()
#                                     logger.info("Lock file %s is created", dfslockfile)
#                                     with open(dfs_path_file_name, 'w') as f:
#                                         logger.info("Writing to file %s is going to start", dfs_path_file_name)
#                                         data['path'].append({
#                                             'Path': dfs_to_ifs_path,
#                                             'DFS Path': path_raw,
#                                             'Requestor': requestor
#                                             })
#                                         json.dump(data, f)
#                                         logger.info("Writing to file completed. Path: %s, DFS Path: %s, Requestor: %s", dfs_to_ifs_path, path_raw, requestor)
#                                     if (os.path.isfile(dfslockfile)):
#                                         try:
#                                             os.remove(dfslockfile)
#                                             while (lock_check_countr < 3):
#                                                 lock_check_countr = lock_check_countr + 1
#                                                 if (os.path.isfile(dfslockfile)):
#                                                     os.remove(dfslockfile)
#                                                 else:
#                                                     logger.info("lock file removed successfully %s", dfslockfile)
#                                                     break
#
#                                         except Exception as e:
#                                             logger.info("Got error while deleting lock file : %s", dfslockfile)
#                                             send_email()
                            else:
                                #open(dfslockfile, 'a').close()
                                #logger.info("Lock file %s is created", dfslockfile)
                                with open(dfs_path_file_name, 'r') as fil:
                                    dfs_val = json.load(fil)
                                dfs_cur_path_lst = []
                                for v in dfs_val['path']:
                                    dfs_cur_path_lst.append(v['Path'])
                                if dfs_to_ifs_path not in dfs_cur_path_lst:
                                    dfs_val['path'].append({
                                        'Path': dfs_to_ifs_path,
                                        'DFS Path': path_raw,
                                        'Requestor': requestor
                                        })
                                    with open(dfs_path_file_name, 'w') as f:
                                        logger.info("Appending to file %s is going to start", dfs_path_file_name)
                                        json.dump(dfs_val, f)
                                        logger.info("Appending to file completed. Path: %s, DFS Path: %s, Requestor: %s", dfs_to_ifs_path, path_raw, requestor)
                                else:
                                    logger.info("Path %s already exists in the file %s", dfs_to_ifs_path, dfs_path_file_name)
                                    msg = cfgobj["Message"]["duplicate_request"]
#                                 if (os.path.isfile(dfslockfile)):
#                                     try:
#                                         os.remove(dfslockfile)
#                                         while (lock_check_countr < 3):
#                                             lock_check_countr = lock_check_countr + 1
#                                             if (os.path.isfile(dfslockfile)):
#                                                 os.remove(dfslockfile)
#                                             else:
#                                                 logger.info("lock file removed successfully %s", dfslockfile)
#                                                 break
#
#                                     except Exception as e:
#                                         logger.info("Got error while deleting lock file : %s", dfslockfile)
#                                         send_email()
                        else:
                            #open(dfslockfile, 'a').close()
                            #logger.info("Lock file %s is created", dfslockfile)
                            with open(dfs_path_file_name, 'w') as f:
                                data['path'].append({
                                    'Path': dfs_to_ifs_path,
                                    'DFS Path': path_raw,
                                    'Requestor': requestor
                                    })
                                json.dump(data, f)
                                logger.info("Writing to file %s completed", dfs_path_file_name)
#                             if (os.path.isfile(dfslockfile)):
#                                 try:
#                                     os.remove(dfslockfile)
#                                     while (lock_check_countr < 3):
#                                         lock_check_countr = lock_check_countr + 1
#                                         if (os.path.isfile(dfslockfile)):
#                                             os.remove(dfslockfile)
#                                         else:
#                                             logger.info("lock file removed successfully %s", dfslockfile)
#                                             break
#
#                                 except Exception as e:
#                                     logger.info("Got error while deleting lock file : %s", dfslockfile)
#                                     send_email()
                    elif (len(dfs_to_ifs_path.split('/')) > 6):
                        if (dfs_to_ifs_path.split('/')[5] == 'apps'):
                            if (os.path.isfile(dfs_path_file_name)):
                                logger.info("File %s exists", dfs_path_file_name)
                                if (os.path.isfile(dfslockfile)):
                                    logger.info("Lock File exists:%s",dfslockfile)
                                    logger.info("Going to write in temporary file %s", tmp_dfs_path_file_name)
                                    with open(tmp_dfs_path_file_name, 'w') as t:
                                        logger.info("File %s opened for writing", tmp_dfs_path_file_name)
                                        data['path'].append({
                                            'Path': dfs_to_ifs_path,
                                            'DFS Path': path_raw,
                                            'Requestor': requestor
                                        })
                                        json.dump(data, t)
                                        logger.info("Writing to temporary file %s completed", tmp_dfs_path_file_name)
                                    logger.info("Going to check whether lock file %s is deleted by cluster script or not",dfslockfile)
                                    while (check_countr < lck_fil_cntr and os.path.isfile(dfslockfile)):
                                        check_countr = check_countr + 1
                                        logger.info("Check counter: %s", str(check_countr))
                                        logger.info("Going to sleep for %s", str(lck_file_wait_time))
                                        time.sleep(lck_file_wait_time)
                                    if (os.path.isfile(dfslockfile)):
                                        logger.info("Lock file %s exists. Cannot process the request", dfslockfile)
                                        msg = cfgobj["Message"]["cluster_script_lock_file_exists"]
                                        logger.info("Going to send email to admins as the lock file %s generated by cluster script is not deleted", lockfile)
                                        admin_temp_val['files'] = dfslockfile
                                        admin_temp_val['sender_mail'] = fromaddr
                                        html = render_template(admin_temp_file, val=admin_temp_val)
                                        send_email(cfgobj["Message"]["lock_file_issue_subject"], html, cfgobj["Mail"]["admin_mail"], fromaddr)
                                    else:
                                        #open(dfslockfile, 'a').close()
                                        #logger.info("Lock file %s is created", dfslockfile)
                                        with open(dfs_path_file_name, 'w') as f:
                                            logger.info("Writing to file %s is going to start", dfs_path_file_name)
                                            data['path'].append({
                                                'Path': dfs_to_ifs_path,
                                                'DFS Path': path_raw,
                                                'Requestor': requestor
                                                })
                                            json.dump(data, f)
                                            logger.info("Writing to file completed. Path: %s, DFS Path: %s, Requestor: %s", dfs_to_ifs_path, path_raw, requestor)
#                                         if (os.path.isfile(dfslockfile)):
#                                             try:
#                                                 os.remove(dfslockfile)
#                                                 while (lock_check_countr < 3):
#                                                     lock_check_countr = lock_check_countr + 1
#                                                     if (os.path.isfile(dfslockfile)):
#                                                         os.remove(dfslockfile)
#                                                     else:
#                                                         logger.info("lock file removed successfully %s", dfslockfile)
#                                                         break
#
#                                             except Exception as e:
#                                                 logger.info("Got error while deleting lock file : %s", dfslockfile)
#                                                 send_email()
                                else:
                                    #open(dfslockfile, 'a').close()
                                    #logger.info("Lock file %s is created", dfslockfile)
                                    with open(dfs_path_file_name, 'r') as fil:
                                        dfs_val = json.load(fil)
                                    dfs_cur_path_lst = []
                                    for v in dfs_val['path']:
                                        dfs_cur_path_lst.append(v['Path'])
                                    if dfs_to_ifs_path not in dfs_cur_path_lst:
                                        dfs_val['path'].append({
                                            'Path': dfs_to_ifs_path,
                                            'DFS Path': path_raw,
                                            'Requestor': requestor
                                            })
                                        with open(dfs_path_file_name, 'w') as f:
                                            logger.info("Appending to file %s is going to start", dfs_path_file_name)
                                            json.dump(dfs_val, f)
                                            logger.info("Appending to file completed. Path: %s, DFS Path: %s, Requestor: %s", dfs_to_ifs_path, path_raw, requestor)
                                    else:
                                        logger.info("Path %s already exists in the file %s", dfs_to_ifs_path, dfs_path_file_name)
                                        msg = cfgobj["Message"]["duplicate_request"]
#                                     if (os.path.isfile(dfslockfile)):
#                                         try:
#                                             os.remove(dfslockfile)
#                                             while (lock_check_countr < 3):
#                                                 lock_check_countr = lock_check_countr + 1
#                                                 if (os.path.isfile(dfslockfile)):
#                                                     os.remove(dfslockfile)
#                                                 else:
#                                                     logger.info("lock file removed successfully %s", dfslockfile)
#                                                     break
#
#                                         except Exception as e:
#                                             logger.info("Got error while deleting lock file : %s", dfslockfile)
#                                             send_email()
                            else:
                                #open(dfslockfile, 'a').close()
                                #logger.info("Lock file %s is created", dfslockfile)
                                with open(dfs_path_file_name, 'w') as f:
                                    data['path'].append({
                                        'Path': dfs_to_ifs_path,
                                        'DFS Path': path_raw,
                                        'Requestor': requestor
                                        })
                                    json.dump(data, f)
                                    logger.info("Writing to file completed. Path: %s, DFS Path: %s, Requestor: %s", dfs_to_ifs_path, path_raw, requestor)
#                                 if (os.path.isfile(dfslockfile)):
#                                     try:
#                                         os.remove(dfslockfile)
#                                         while (lock_check_countr < 3):
#                                             lock_check_countr = lock_check_countr + 1
#                                             if (os.path.isfile(dfslockfile)):
#                                                 os.remove(dfslockfile)
#                                             else:
#                                                 logger.info("lock file removed successfully %s", dfslockfile)
#                                                 break
#
#                                     except Exception as e:
#                                         logger.info("Got error while deleting lock file : %s", dfslockfile)
#                                         send_email()
                        else:
                            msg = cfgobj["Message"]["path_above_l7"]

                    else:
                        msg = cfgobj["Message"]["path_above_l7"]


                else:
                    msg = cfgobj["Message"]["incorrect_location"]
            else:
                msg = cfgobj["Message"]["incorrect_region"]
        else:
            msg = cfgobj["Message"]["not_tcs_path"]

    return jsonify({'mesage': msg})

