#!/usr/bin/python

# HTML write service module

##################################################################################################
###
### Created by: Allan Phoenix
###
### Last Update: 2017-12-18
###
### Description:
###
### Procedures to open results files, write to results files and create links to results files on the main 
### testbed webpage 
###
### web module:
###
###   Class:
###   
###   - webFile 
###   
###   Methods:  
###   
###   - file_add_header
###   - file_write
###   - file_close
###   
###
### Functions (i.e. not object oriented)
###
###   - make_results_file
###   - update_results_page
###
###
### Version control:
###
### v1:
###        - Creation.
###
###
### Usage:
###
### import web                                               # import web module
###
### results_file = web.make_results_file(test_case)            # open unique results with current day/time timestamp
###                                                          # passing in, for example, the name of the current test
###                                                          # as a unique identifier
###
### web_out = web.webFile(results_file,'w')                  # Create a web object from the newly opened results file
###
### web_out.file_add_header()                                  # Add html header info to the file needed for changing the 
###                                                          # colour of text
###
### web_out.file_write("line 1")                              # writes "INFO: line 1" to the console and to the web page in black  
###
### web_out.file_write("line 2", log_msg='PASS')              # writes "INFO: line 2" to the console and to the web page in green  
###
### web_out.file_write("line 3", log_msg='OK')                # writes "INFO: line 3" to the console and to the web page in green  
###
### web_out.file_write("line 4", log_msg='ERROR')             # writes "ERROR: line 4" to the console and to the web page in red  
###
### web_out.file_write("line 5", log_msg='FAIL')              # writes "ERROR: line 5" to the console and to the web page in red  
###
### web_out.file_close()                                      # adds in </body> and </html>, closes the web file
###
### web.update_results_page (results_file, test_result)        # Update the testbed results page with a link to the test results 
###                                                          # If test_result = 'PASS' or 'OK' the link is green
###                                                          # Otherwise the link is red
### 
### web.update_results_page (results_file, test_result, notes) # Optionally pass in tesxt 'notes' - this displays text when the cursor is 
###                                                          # hovered over the results link 
### 
### 
### del web_out                                              # delete web object
###
###

import os
import logging
import getpass

from datetime import *

def make_results_file(testbed_name,test_name):

    # Open results file

    now = datetime.now()
    month_text = now.strftime("%B")
    now = str(now)
    now = now.replace(" ","-")

    year  = date.today().year
    month = date.today().month
    day   = date.today().day

    results_dir          = '/var/www/html/results/' 
    testbed_dir          = results_dir + testbed_name
    testbed_results_file = testbed_dir + '/results.html'
    test_user            = getpass.getuser()

    # Look for results directory - create if not present
    if not os.path.isdir("%s" %(results_dir)):
        print("Results directory %s does not exist, creating it" %(results_dir))
        os.makedirs("%s" %(results_dir), '0777')

        
    # Look for testbed directory - create if not present
    if not os.path.isdir("%s" %(testbed_dir)):
        print("Testbed directory %s does not exist, creating it" %(testbed_dir))
        os.makedirs("%s" %(testbed_dir), '0777')

        print("Create main results page for testbed %s" %(testbed_name))
        print("FILE =  %s" %(testbed_results_file))
        
        testbed_results_html = open(testbed_results_file,'a')

        testbed_results_html.write("<html>\n")
        testbed_results_html.write("<title>Automation Results - %s</title>\n" %(testbed_name))
        testbed_results_html.write("<body>\n")
        testbed_results_html.write("<font size = 2 face=courier color=black>\n")
        testbed_results_html.write("<br>\n")
        testbed_results_html.write("<h2>Automation Results - %s</h2>\n" %(testbed_name))
        testbed_results_html.write("<br>\n")
        testbed_results_html.close()

    year_file  = str(testbed_dir) + "/" + str(year) + "/" + str(year)  + ".html"
    month_file = str(testbed_dir) + "/" + str(year) + "/" + str(month) + "/" + str(month) + ".html"
    day_file   = str(testbed_dir) + "/" + str(year) + "/" + str(month) + "/" + str(day) + "/" + str(day) + ".html"
    file       = str(testbed_dir) + "/" + str(year) + "/" + str(month) + "/" + str(day) + "/" + str(test_user) + "_" + str(test_name) + "-" + now + ".html"

    year_link  = str(year)  + "/" + str(year)  + ".html"
    month_link = str(month) + "/" + str(month) + ".html"
    day_link   = str(day)   + "/" + str(day)   + ".html"

    # Look for year directory - create if not present
    if not os.path.isdir("%s/%s" %(testbed_dir,year)):
        results_file = "%s/results.html" %testbed_dir
        os.makedirs("%s/%s" %(testbed_dir,year), '0777')
        print("INFO: Update results.html file with link to %s html file in %s directory" %(year,year))
        results = open(results_file, 'a')
        results.write("<a href=%s>%s</a>\n" %(year_link,year))
        results.write("<br>")
        results.close()

        year_html = open(year_file,'a')
        year_html.write("<html>\n")
        year_html.write("<title>%s Automation Results - %s</title>\n" %(year,testbed_name))
        year_html.write("<body>\n")
        year_html.write("<font size = 2 face=courier color=black>\n")
        year_html.write("<br>\n")
        year_html.write("<h2> %s Automation Results - %s</h2>\n" %(year,testbed_name))
        year_html.write("<br>\n")
        year_html.close()


    # Look for month directory - create if not present
    if not os.path.isdir("%s/%s/%s" %(testbed_dir,year,month)):
        os.makedirs("%s/%s/%s" %(testbed_dir,year,month), '0777')
        print("INFO: Update %s.html file with link to %s html file in %s directory" %(year,month,month))

        year_results = open(year_file, 'a')
        year_results.write("<a href=%s>Month %s</a>\n" %(month_link,month))
        year_results.write("<br>")
        year_results.close()

        month_html = open(month_file,'a')
        month_html.write("<html>\n")
        month_html.write("<title>%s %s Automation Results - %s</title>\n" %(month_text,year,testbed_name))
        month_html.write("<body>\n")
        month_html.write("<font size = 2 face=courier color=black>\n")
        month_html.write("<br>\n")
        month_html.write("<h2> %s %s Automation Results - %s</h2>\n" %(month_text,year,testbed_name))
        month_html.close()

    # Look for day directory - create if not present
    if not os.path.isdir("%s/%s/%s/%s" %(testbed_dir,year,month,day)):
        print("INFO: Creating %s html file in %s directory" %(day,day))
        os.makedirs("%s/%s/%s/%s" %(testbed_dir,year,month,day), '0777')
        print("INFO: Update %s.html file with link to %s html file in %s directory" %(month,day,day))

        month_results = open(month_file, 'a')
        month_results.write("<br>")
        month_results.write("<a href=%s>Day %s</a>\n" %(day_link,day))
        month_results.close()

        day_html = open(day_file,'a')
        day_html.write("<html>\n")
        day_html.write("<title> %s %s %s Automation Results - %s</title>\n" %(day,month_text,year,testbed_name))
        day_html.write("<body>\n")
        day_html.write("<font size = 2 face=courier color=black>\n")
        day_html.write("<br>\n")
        day_html.write("<h2> %s %s %s Automation Results - %s </h2>\n" %(day,month_text,year,testbed_name))

        day_html.close()


    print("INFO: Results file is %s" %(file))
    return file


def update_results_page (testbed_name,results_file,result,notes="NONE"):

    year  = date.today().year
    month = date.today().month
    day   = date.today().day

    syear  = str(year)
    smonth = str(month)
    sday   = str(day)

    webfile = str("/var/www/html/results/") + str(testbed_name) + "/" + str(year) + "/" + str(month) + "/" + str(day) + "/" + str(day) + ".html"

    if result == "PASS" or result == 'OK':
        style = 'color:#33CC00'
    else:
        style = 'color:#FF0000'

    # dlink = displayed link
    # rlink = real link
    replace = "/var/www/html/results/" + testbed_name + "/" + syear + "/" + smonth + "/" + sday + "/" 

    dlink  = results_file.replace(replace, "")
    dlink  = dlink.replace(".html","")

    rlink  = results_file.replace("/var/www/html","")

    f = open(webfile, 'a')

    f.write("<br>\n")
    f.write("<a href=%s title=%s style=%s> %s  %s </a>\n" %(rlink,notes,style,dlink,result))

    f.close()


#class webFile(file):
#
#    def __init__(self, name, mode = 'r'):
#        self = file.__init__(self, name, mode)
#
#
#    def file_add_header(self):
#
#        self.writelines("<html>\n")
#        self.writelines("<style>\n")
#        self.writelines("black {white-space: pre-wrap;\n")
#        self.writelines("color:black;\n")
#        self.writelines("font-family: Courier, monospace;\n")
#        self.writelines("font-size: 14;\n")
#        self.writelines("font-weight: 400;\n")
#        self.writelines("font-size: 14;\n")
#        self.writelines("font-weight: 400;\n")
#        self.writelines("line-height: 20px;\n")
#        self.writelines("margin-top:0;\n")
#        self.writelines("margin-bottom:0;\n")
#        self.writelines("display: block\n")
#        self.writelines("}\n")
#        self.writelines("green {white-space: pre-wrap;\n")
#        self.writelines("color:green;\n")
#        self.writelines("font-family: Courier, monospace;\n")
#        self.writelines("font-size: 14;\n")
#        self.writelines("font-weight: 400;\n")
#        self.writelines("line-height: 20px;\n")
#        self.writelines("margin-top:0;\n")
#        self.writelines("margin-bottom:0;\n")
#        self.writelines("display: block\n")
#        self.writelines("}\n")
#        self.writelines("red {white-space: pre-wrap;\n")
#        self.writelines("color:red;\n")
#        self.writelines("font-family: Courier, monospace;\n")
#        self.writelines("font-size: 14;\n")
#        self.writelines("font-weight: 400;\n")
#        self.writelines("line-height: 20px;\n")
#        self.writelines("margin-top:0;\n")
#        self.writelines("margin-bottom:0;\n")
#        self.writelines("display: block\n")
#        self.writelines("}\n")
#        self.writelines("</style>\n")
#        self.writelines("<body>\n")
#
#
#    def file_write(self, string, log_msg='NONE'):
#        mylog=logging.getLogger(__name__)
#        if log_msg == 'PASS' or log_msg == 'OK':
#            print("INFO: %s" %(string))
#            mylog.info("%s" %(string) )
#            self.writelines("<green>INFO: %s</green>\n" %(string))
#        elif log_msg == 'FAIL' or log_msg == 'ERROR':
#            print("ERROR: %s" %(string))
#            mylog.info("%s" %(string) )
#            self.writelines("<red>ERROR: %s</red>\n" %(string))
#        elif log_msg == 'DEBUG':
#            print("ERROR: %s" %(string))
#            mylog.info("%s" %(string) )
#            self.writelines("<black>DEBUG: %s</black>\n" %(string))
#        else:
#            print("INFO: %s" %(string))
#            mylog.info("%s" %(string) )
#            self.writelines("<black>INFO: %s</black>\n" %(string))
#
#        return None
#   
#    
#    def file_close(self):
#
#        self.writelines("</body>\n")
#        self.writelines("</html>\n")
#        self.close()
