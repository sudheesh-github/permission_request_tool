#!/usr/bin/python

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import yaml
import os
from datetime import date, datetime
import logging
import time

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


def send_email():
    MESSAGE = MIMEMultipart('alternative')
    MESSAGE['subject'] = "Lock file removal failed"
    MESSAGE['To'] = cfgobj["Mail"]["admin_mail"]
    MESSAGE['From'] = cfgobj["Mail"]["mail_from"]
    rcpt = cfgobj["Mail"]["admin_mail"]
    restmsg = """
    Hi,
    
    Removal of lock file from toprocess folder through Web code failed. Please check and delete it manually so that it can be processed. 
        
    Thanks & Regards,
    TCSS Team
    """
    body = restmsg
    HTML_BODY = MIMEText(body, 'html')
    MESSAGE.attach(HTML_BODY)
    server = smtplib.SMTP('localhost')
    server.sendmail(FROM, rcpt.split(','), MESSAGE.as_string())
    server.quit()


@app.route('/home')
def home():
    user = request.headers.get('X-WEBAUTH-LNXUSER')
    session['email'] = user.split('@')[0].lower() + '@shell.com'
    return render_template('index.html', host = hst, port = prt, email = session.get('email'))

@app.route('/tcspath', methods = ['POST', 'GET'])
def tcs_path():
    requestor = session.get('email')
    main_dir_path = cfgobj["Main"]["files_dir_path"]
    envrnmnt = cfgobj["Main"]["environment"]
    foldr = cfgobj["Main"]["toprocessfolder"]
    check_countr = 0
    pathtype = request.args.get('pathtype','')
    path = request.args.get('path','')
    logger.info("Requestor:%s PathType:%s Path:%s",requestor,pathtype,path)
    #path = request.form["path"]
    msg = 'Thank you! Request Submitted Successfully.You will get information in email within 15 minutes'
    if (pathtype == 'ifspath'):
        path_list = path.split('/')
        if (len(path_list) > 7):
            if (path_list[1] == 'ifs' and path_list[2] in cfgobj["Main"]["regions"] and path_list[3] in cfgobj["Main"]["regions"][path_list[2]] and path_list[4] in cfgobj["Main"]["level3struct"]):
                site = path_list[3]
                path_name = ''
                file_name = requestor + '.csv'
                path_file_name = main_dir_path + site + '/' + envrnmnt + "/" + foldr + "/" + file_name
                logger.info("File to be created in toprocess folder : %s", path_file_name)
                lockfile = path_file_name + '.lck'
                if (os.path.isfile(path_file_name)):
                    if (os.path.isfile(lockfile)):
                        logger.info("Lock File exists:%s",lockfile)
                        while (check_countr < lck_fil_cntr and os.path.isfile(lockfile)):
                            check_countr = check_countr + 1
                            logger.info("Check counter: %s", str(check_countr))
                            time.sleep(lck_file_wait_time)
                        if (os.path.isfile(lockfile)):
                            logger.info("Lock file created by cluster script is not removed. %s", lockfile)
                            msg = "Request Cannot be submitted right now. Please wait for sometime and re-submit after 10-15 minutes"
                        else:
                            open(lockfile, 'a').close()
                            logger.info("Lock file %s created", lockfile)
                            with open(path_file_name, 'w') as f:
                                logger.info("File %s opened for writing", path_file_name)
                                f.write("Path,DFS Path,Requestor,Permission\n")
                                f.write(path + "," + "NA," + requestor + "," + "\n")
                                logger.info("Writing to file %s completed", path_file_name)
                            if (os.path.isfile(lockfile)):
                                try:
                                    os.remove(lockfile)
                                    logger.info("lock file removed successfully %s", lockfile)
                                except Exception as e:
                                    logger.info("Got error while deleting lock file : %s", lockfile)
                                    send_email()
                        
                    else:
                        logger.info("Lock file %s does not exist", lockfile)
                        open(lockfile, 'a').close()
                        with open(path_file_name, 'r') as fil:
                            val = fil.readlines()
                        cur_path_lst = []
                        for v in val:
                            cur_path_lst.append(v.split(',')[0])
                        if path not in cur_path_lst:
                            logger.info("Opening the file %s to append path %s", path_file_name, path)
                            with open(path_file_name, 'a') as f:
                                f.write(path + "," + "NA," + requestor + "," + "\n")
                        else:
                            logger.info("Path %s already exists in the file %s", path, path_file_name)
                            msg = "You have already submitted the request for this Path. Please wait you will receive the information over email."
                        if (os.path.isfile(lockfile)):
                            try:
                                os.remove(lockfile)
                                logger.info("lock file removed successfully %s", lockfile)
                            except Exception as e:
                                logger.info("Got error while deleting lock file : %s", lockfile)
                                send_email()
                else:
                    open(lockfile, 'a').close()
                    logger.info("Lock file %s is created", lockfile)
                    with open(path_file_name, 'w') as f:
                        logger.info("File %s created", path_file_name)
                        f.write("Path,DFS Path,Requestor,Permission\n")
                        f.write(path + "," + "NA," + requestor + "," + "\n")
                        logger.info("Writing to file %s completed", path_file_name)
                    if (os.path.isfile(lockfile)):
                        try:
                            os.remove(lockfile)
                            logger.info("lock file removed successfully %s", lockfile)
                        except Exception as e:
                            logger.info("Got error while deleting lock file : %s", lockfile)
                            send_email()
                    
                
            else:
                msg = 'Please enter correct path'
        else:
            msg = 'Please enter correct path'
    if (pathtype == "dfspath"):
        path_raw = repr(path)
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
                    if ('nobackup' in path_list):
                        fnl_path = locn_path + 'nobackup/'
                    else:
                        fnl_path = locn_path + 'backup/'

                    for i in range(4,len(path_list)):
                        if ('.' in path_list[i]):
                            pth = path_list[i].split('.')
                            for j in pth:
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
                    dfslockfile = dfs_path_file_name + '.lck'
                    dfs_to_ifs_path = '/' + fnl_path 
                    if (os.path.isfile(dfs_path_file_name)):
                        logger.info("File %s exists", dfs_path_file_name)
                        if (os.path.isfile(dfslockfile)):
                            logger.info("Lock File exists:%s",dfslockfile)
                            while (check_countr < lck_fil_cntr and os.path.isfile(dfslockfile)):
                                check_countr = check_countr + 1
                                logger.info("Check counter: %s", str(check_countr))
                                time.sleep(lck_file_wait_time)
                            if (os.path.isfile(dfslockfile)):
                                logger.info("Lock file %s exists. Cannot process the request", dfslockfile)
                                msg = "Request Cannot be submitted right now. Please wait for sometime and re-submit after 10-15 minutes"
                            else:
                                open(dfslockfile, 'a').close()
                                logger.info("Lock file %s is created", dfslockfile)
                                with open(dfs_path_file_name, 'w') as f:
                                    logger.info("Writing to file %s is going to start", dfs_path_file_name)
                                    f.write("Path,DFS Path,Requestor,Permission\n")
                                    f.write(dfs_to_ifs_path + "," + path_raw + "," + requestor + "," + "\n")
                                    logger.info("Writing to file completed. Path: %s, DFS Path: %s, Requestor: %s", dfs_to_ifs_path, path_raw, requestor)
                                if (os.path.isfile(dfslockfile)):
                                    try:
                                        os.remove(dfslockfile)
                                        logger.info("lock file removed successfully %s", dfslockfile)
                                    except Exception as e:
                                        logger.info("Got error while deleting lock file : %s", dfslockfile)
                                        send_email()
                        else:
                            open(dfslockfile, 'a').close()
                            logger.info("Lock file %s is created", dfslockfile)
                            with open(dfs_path_file_name, 'r') as fil:
                                dfs_val = fil.readlines()
                            dfs_cur_path_lst = []
                            for v in dfs_val:
                                dfs_cur_path_lst.append(v.split(',')[0])
                            if dfs_to_ifs_path not in dfs_cur_path_lst:
                                with open(dfs_path_file_name, 'a') as f:
                                    logger.info("Appending to file %s is going to start", dfs_path_file_name)
                                    f.write(dfs_to_ifs_path + "," + path_raw + "," + requestor + "," + "\n")
                                    logger.info("Appending to file completed. Path: %s, DFS Path: %s, Requestor: %s", dfs_to_ifs_path, path_raw, requestor)
                            else:
                                logger.info("Path %s already exists in the file %s", dfs_to_ifs_path, dfs_path_file_name)
                                msg = "You have already submitted the request for this Path. Please wait you will receive the information over email."
                            if (os.path.isfile(dfslockfile)):
                                try:
                                    os.remove(dfslockfile)
                                    logger.info("lock file removed successfully %s", dfslockfile)
                                except Exception as e:
                                    logger.info("Got error while deleting lock file : %s", dfslockfile)
                                    send_email()
                    else:
                        open(dfslockfile, 'a').close()
                        logger.info("Lock file %s is created", dfslockfile)
                        with open(dfs_path_file_name, 'w') as f:
                            f.write("Path,DFS Path,Requestor,Permission\n")
                            f.write(dfs_to_ifs_path + "," + path_raw + "," + requestor + "," + "\n")
                        if (os.path.isfile(dfslockfile)):
                            try:
                                os.remove(dfslockfile)
                                logger.info("lock file removed successfully %s", dfslockfile)
                            except Exception as e:
                                logger.info("Got error while deleting lock file : %s", dfslockfile)
                                send_email()
                    
                    
                else:
                    msg = "Please enter correct location in the path"
            else:
                msg = "please enter correct region in the path"
        else:
            msg = "It is not a TCS path"

    #return render_template('index.html', host = hst, port = prt, otpt = msg, email = requestor)
    return jsonify({'mesage': msg})
#app.run(port=5000)

