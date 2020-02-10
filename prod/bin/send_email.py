#!/usr/bin/python

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import yaml
import os
import glob
import csv
import re
import logging
from datetime import date, datetime
import time


dir_path = os.path.dirname(os.path.realpath(__file__))
cfgfile = dir_path + '/../etc/config/main.cfg'

with open(cfgfile, 'r') as f:
    cfgobj = yaml.load(f)

today = str(datetime.strftime(date.today(), '%Y_%m_%d'))

processed_folder = cfgobj["Main"]["processedfolder"]

dir_path = os.path.dirname(os.path.realpath(__file__))
scriptname = os.path.basename(__file__).split(".")[0]

check_countr = 0
lck_fil_cntr = int(cfgobj["Main"]["lockfile_check_counter"])
lck_file_wait_time = int(cfgobj["Main"]["lockfile_wait_time"])


logfilenam = dir_path + '/../logs/' + scriptname + '_' + today + '.log'
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)
ch = logging.FileHandler(logfilenam)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')
ch.setFormatter(formatter)
logger.addHandler(ch)

def get_files_list(path):
    logger.info("Inside get_files_list function")
    logger.info("Going to get list of files from : %s", path)
    file_list = glob.glob(path + "/*.csv")
    if (file_list):
        logger.info("Count of files in the path is: %s", str(len(file_list)))
    else:
        logger.info("No files in the path")
    return file_list


def send_email(SUBJECT, BODY, TO, FROM):
    MESSAGE = MIMEMultipart('alternative')
    MESSAGE['subject'] = SUBJECT
    MESSAGE['To'] = TO
    MESSAGE['From'] = FROM
    rcpt = TO
    HTML_BODY = MIMEText(BODY, 'html')
    MESSAGE.attach(HTML_BODY)
    server = smtplib.SMTP('localhost')
    server.sendmail(FROM, rcpt.split(','), MESSAGE.as_string())
    server.quit()


def process_output():
    #msg = MIMEMultipart()
    logger.info("Inside process_output function")
    fromaddr = cfgobj["Mail"]["mail_from"]
    main_path = cfgobj["Mail"]["main_mount_path"]
    envrnmnt = cfgobj["Main"]["environment"]
    loc_list = cfgobj["Mail"]["region_mapped_path"].split(',')
    for l in loc_list:
        logger.info("Going to process for location: %s", l)
        locpth = main_path + l + "/" + envrnmnt + "/" + processed_folder
        list_of_files = get_files_list(locpth)
        for lf in list_of_files:
            logger.info("Going to process file: %s", lf)
            lckfile = lf + '.lck'
            if (os.path.isfile(lckfile)):
                logger.info("Lock File exists:%s",lckfile)
                while (check_countr < lck_fil_cntr and os.path.isfile(lckfile)):
                    check_countr = check_countr + 1
                    logger.info("Check counter: %s", str(check_countr))
                    time.sleep(lck_file_wait_time)
            if (os.path.isfile(lckfile)):
                logger.info("Lock file still exists which was created we b interface code %s", lckfile)
                next(lf)
            else:
                with open(lf, 'r') as f:
                    reader = csv.reader(f)
                    next(reader)
                    for val in reader:
                        if (len(val) > 1):
                            msg_head = """
                                    <head>
                                    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                                    <title>html title</title>
                                    <style type="text/css" media="screen">
                                    table, th, td{
                                        border: 1px inset lightsteelblue;
                                    
                                    }
                                    </style>
                                    </head>
                                    """
                            perm_str = ""
                            pth = val[0]
                            requestor = val[2]
                            dfspath = val[1]
                            if (dfspath != "NA"):
                                dfcorval = dfspath.decode('string_escape').replace("u'", "'").replace("'", "")
                            perm = val[3]
                            level7path = val[4]
                            level7security = val[5]
                            perm_lst = perm.split(";")
                            cnt = len(perm_lst)
                            logger.info("Permission List Count: %s", cnt)
                            for a in range(0, cnt):
                                if (perm_lst[a]):
                                    print perm_lst[a]
                                    pval = perm_lst[a].split("->")[1]
                                    val1 = re.sub(r'.* dir_gen_', 'dir_gen_', pval)
                                    pval_lst = val1.split("|")
                                    fval = ''
                                    for i in pval_lst:
                                        if ("dir_gen" in i):
                                            fval = fval + i.split("dir_gen_")[1] + ","
                                    fin_val = fval[:-1]
                                    perm_str = perm_str + '<tr>' + '<td>' + perm_lst[a].split("->")[0] + "</td>" + "<td>" + fin_val + "</td>" + "</tr>"
                            fnl_perm_str = "<table>" + "<tr>" + "<th>" + "Group" + "</th>" + "<th>" + "Permissions" + "</th>" + "</tr>" + perm_str + "</table>"
                            print fnl_perm_str
                            sendingaddr =  requestor
                            if (dfspath != "NA"):
                                pth = dfcorval
                            if (level7security != ''):
                                if (level7security != "NA"):
                                    topfoldermsg = "<p>" + "Top level folder for the requested path has security style as: " + level7security + "</p>"
                                else:
                                    topfoldermsg = ''
                            else:
                                topfoldermsg = ''
                            signature_msg = "<p>" + "TCSS Team" + "</br>" + cfgobj["Mail"]["mail_from"] + "</p>"
                            subject = "Access Rights - Shared Folder - " + pth
                            nam = requestor.split("@")[0].split(".")[0].capitalize()
                            bod_cntnt = "<p>" + "Hi " + nam + "," + "</p>" + "<p>" + "Please find the requested information below: " + "</p>" + "<h3><u>" + "Path" + "</u></h3>" + pth + "</br>" + "<h3><u>" + "Group Information" + "</u></h3>"
                            final_html_msg = msg_head + "<body>" + bod_cntnt + fnl_perm_str + "</br>" + topfoldermsg + signature_msg + "</body>"
                            send_email(subject, final_html_msg, sendingaddr, fromaddr)
                            logger.info("Mail Sent to: %s", sendingaddr)
                        
                try:    
                    os.remove(lf)
                    logger.info("File Deleted from processed folder : %s", lf)
                except Exception as e:
                    logger.info("File %s could not be deleted from processed folder", lf)
                    logger.info("Error is: %s", str(e))
                    


if __name__ == "__main__":
    process_output()
    
