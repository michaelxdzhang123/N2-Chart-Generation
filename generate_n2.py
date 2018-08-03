# Sam Spelsberg IVV intern summer 2018
# generate_n2.py

import sqlite3 as sql
import os
from bs4 import BeautifulSoup
import re
from regexMethodSignatures import regexClassName, regexParams, regexMethodName, regexReturnTypes
from collect_globals import collectGlobals
from create_tables import createTables, globalsTable
from data_collection import createInterfaceGraphFromReport, getInterfaceText, getReturnText, getMethodSignature, createInterfaceGraphFromDB, methodInDB, classInDB
import xlsxwriter as xlsx
from time import sleep
import sys


if os.path.isfile('n2_chart.xlsx'): # block to ensure that the person has the excel sheet closed or moved from the directory before script starts
    try:
        excel_sheet = open('n2_chart.xlsx', 'r+')
    except:
        print('\nFATAL ERROR: Please close or move the file \'n2_chart.xlsx\' in this directory and run this script again')
        input()
        exit()
    excel_sheet.close()


print("Type the name of the function you wish to start the N2 chart with, in the format <ClassName>::<FunctionName>\nIf there is no class prefix, search just the function name")
start_func = input().strip()  # take in the start method, must be in the correct Case


print("\nNow please input the file path of the <project>_html folder (Do not include end \'\\\')")
folder_path = input().strip()  # take the folder path to the HTML reports


first = start_func[0]
try:   # get the first letter of the method for opening the file path in the HTML report
    if not first.isalnum():
        first = "Non-Alpha"
except:
    pass

try:  # simple check to make sure that the method that was passed in as well as the folder path works before proceeding
    dict_html = open(folder_path + '\progunit_xref_' + first + '.html', encoding='utf8')
except Exception as e:
    print("ERROR: Bad directory request, double check path or function name. Press enter to quit")
    k = input()
    exit()


#---------------------------Set up database---------------------------#

# check to see if db is there
if not os.path.isfile("interfaces.db"): # if it is not then create new
    print("\nNo \'interfaces.db\' file not found, would you like to use your own .db file? (Y/N)")
    k = input()
    k = k.strip()
    while( k not in ['N', 'n', 'Y', 'y' ] ):
        print('Invalid input, try again')
        k = input()
    if k == 'Y' or k == 'y':
        print('What is the file path to the .db file?')
        customdb = input()
        customdb = customdb.strip()
        connection = sql.connect(customdb)
        crsr = connection.cursor()
        print('Connected to alternative .db file.')
    elif k == 'N' or k == 'n':
        connection = sql.connect("interfaces.db")   # fresh db
        # cursor
        crsr = connection.cursor()
        createTables(crsr)  # calls the create tables inline SQL method in the other .py file
else:   #it's there prompt the user to choose whether they want to use the existing one or recreate another one
    print("\nInterfaces database found, would you like to use interfaces.db database? (Y/N)")
    k = input()
    k = k.strip()
    while( k not in ['N', 'n', 'Y', 'y' ] ):
        print('Invalid input, try again')
        k = input()
        k = k.strip()
    if k == 'y' or k == 'Y':
        print("Ok, using existing")
        connection = sql.connect("interfaces.db")
        crsr = connection.cursor()
    elif k == 'n' or k == 'N':  # if they don't want to use the existng database then overwrite the current interfaces.db
        print('Would you like to select a different .db file to use? (Y/N) \n WARNING: Selecting \'N\' will delete interfaces.db')
        k = input()
        k = k.strip()
        while( k not in ['N', 'n', 'Y', 'y' ] ):
            print('Invalid input, try again')
            k = input()
            k = k.strip()
        if k == 'N' or k == 'n':
            print("Ok, creating new interfaces.db file")
            os.remove('interfaces.db')
            connection = sql.connect("interfaces.db")
            crsr = connection.cursor()
            createTables(crsr)
        elif k=='Y' or k == 'y':
            print('What is the file path to the .db file?')
            customdb = input()
            customdb = customdb.strip()
            connection = sql.connect(customdb)
            crsr = connection.cursor()
            print('Connected to alternative .db file.')
    else:
        print("ERROR: Invalid input")
        exit()

USE_GLOBALS = globalsTable(folder_path)  # this accesses the globalsTable method in the create_tables.py
# returns a boolean of whether the user is going to use global variables or not

#---------------------------End DB creation-------------------------------#
# Now topologically sort the graph for the methods table

from collections import deque

GRAY, BLACK = 0, 1

def topological(graph):
    """method to topologically sort the graph of interfaces, returns sorted 1D list"""
    order, enter, state = deque(), set(graph), {}
    def dfs(node):
        state[node] = GRAY
        for k in graph.get(node, ()):
            sk = state.get(k, None)
            if sk == GRAY: raise ValueError("cycle")
            if sk == BLACK: continue
            enter.discard(k)
            dfs(k)
        order.appendleft(node)
        state[node] = BLACK

    while enter: dfs(enter.pop())
    return order

#-----------------Data collection----------------#
exists = methodInDB(start_func, '', crsr )  # tests methodInDB to see if the method that was initially passed into exists
if exists[0] == False: # if the database was just created have to collect interfaces fresh
    report = createInterfaceGraphFromReport(start_func, folder_path, crsr) # call to data_collection.py
    interface_graph = report[0]
    start_func_dict_link = report[1][0] # have to get the starting dict link because the start function isn't provided one at the start
    sys.stdout.write('\r')
    sys.stdout.write("Generating Interface Graph [%-50s]" % ('='*50))  # fills up the search bar to show it has finished
    sys.stdout.flush()
    print("\nGraph of interfaces generated.\n")
    populate_db = True # set this boolean to True to indicate we have to enter the double loop below to collect and insert data
elif exists[0] == True:    # the method we want is already there, so we can create the interface graph from the DB
    print("Method found in database, creating graph from database.")
    interface_graph = createInterfaceGraphFromDB(start_func, exists[1], crsr) # create interface graph
    print("\nGraph of interfaces generated.\n")
    populate_db = False # this means we won't have to go and collect and insert data


#MORE VOCAB:
#  full name = class::name
#  method_sig when referenced in terms of the getMethodSignature function is a list that has the method signature [0] and the method text as [1]
#-----------------populate methods, classes, and interfaces tables-----------------#
if populate_db:
    all_methods = []
    all_classes = []  # lists to keep track of methods and classes that have already been handled
    loading_count = 0
    for key in interface_graph:   # loop through the keys in the interface graph
        if len(key) == 0:  # if for some reason we have an edge case key of ""
            continue

        caller_method_sig = getMethodSignature(key, folder_path) # call to get the method sig and method text

        # break up the method into class and method name and dict link for insert into DB
        caller_full_name = key.split('::')
        if len(caller_full_name) == 1:
            caller_class_name = 'Unknown'
            tmp = caller_full_name[0].split('#')
            caller_method_name = tmp[0].strip()
            caller_dict_link = tmp[1].strip()
        elif len(caller_full_name) > 1:
            caller_class_name = caller_full_name[0].strip()
            tmp = caller_full_name[len(caller_full_name)-1].split('#')
            caller_dict_link = tmp[1].strip()
            caller_method_name = '::'.join(caller_full_name[1:])
            caller_method_name = caller_method_name[:caller_method_name.find('#')]

        for i in ['private:', 'protected:', 'public:']:  # if the method is a header declaration that happens to have one of these words in the header, remove it
            if i in caller_method_sig[0]:
                caller_method_sig[0] = caller_method_sig[0].replace(i, '')
                caller_method_sig[0] = caller_class_name + '::' + caller_method_sig[0].strip()
                break
        # now regex the parameters and the return types from the method signature
        caller_return_type = regexReturnTypes(caller_method_sig[0])
        caller_params = regexParams(caller_method_sig[0])

        if key not in all_methods and not methodInDB(key.split('#')[0].strip(), caller_dict_link, crsr)[0]:
            all_methods.append(key)     # if the method is not already in the database or been inserted this execution of the script
            if caller_class_name not in all_classes and not classInDB(caller_class_name, crsr):  # if we haven't added the class yet this iteration add it to the database
                all_classes.append(caller_class_name)
                crsr.execute("INSERT INTO classes (class_name) VALUES (?);", (caller_class_name,)) #inline sql insert
                connection.commit()
            crsr.execute( "INSERT INTO methods (method_signature, class_name, method_name, return_type, params, method_text, dict_link) VALUES (?, ?, ?, ?, ?, ?, ?);", (caller_method_sig[0], caller_class_name,
            caller_method_name, caller_return_type, caller_params, caller_method_sig[1], caller_dict_link) ) #insert for methods db
            connection.commit()

        for val in interface_graph[key]:  # loop through callee methods that correspond to the caller (key)
            if len(val) == 0: # edge case handler
                continue
            if loading_count > 50:
                loading_count = 0
            sys.stdout.write('\r')
            sys.stdout.write("Collecting and Inserting Data [%-50s]" % ('='*loading_count))
            sys.stdout.flush()  # output for the loading bar display on the screen
            loading_count += 1

            callee_method_sig = getMethodSignature(val, folder_path) # call to get the method signature and the method text
            # break up the method into class and method name and dict link for insert into DB
            callee_full_name = val.split('::')
            if len(callee_full_name) == 1:
                callee_class_name = 'Unknown'
                tmp = callee_full_name[0].split('#')
                callee_method_name = tmp[0].strip()
                callee_dict_link = tmp[1].strip()
            elif len(callee_full_name) > 1:
                callee_class_name = callee_full_name[0].strip()
                tmp = callee_full_name[len(callee_full_name)-1].split('#')
                callee_dict_link = tmp[1].strip()
                callee_method_name = '::'.join(callee_full_name[1:])
                callee_method_name = callee_method_name[:callee_method_name.find('#')]

            for i in ['private:', 'protected:', 'public:']: # if the method is a header declaration that happens to have one of these words in the header, remove it
                if i in callee_method_sig[0]:
                    callee_method_sig[0] = callee_method_sig[0].replace(i, '')
                    callee_method_sig[0] = callee_class_name + '::' + callee_method_sig[0].strip()
                    break
            # now regex the parameters and the return types from the method signature
            callee_return_type = regexReturnTypes(callee_method_sig[0])
            callee_params = regexParams(callee_method_sig[0])

            if val not in all_methods and not methodInDB(val.split('#')[0].strip(), callee_dict_link, crsr)[0]:
                all_methods.append(val)  # same as above, insert classes and methods that haven't been captured yet
                if callee_class_name not in all_classes and not classInDB(callee_class_name, crsr):
                    all_classes.append(callee_class_name)
                    crsr.execute("INSERT INTO classes (class_name) VALUES (?);", (callee_class_name,))
                    connection.commit()
                crsr.execute( "INSERT INTO methods (method_signature, class_name, method_name, return_type, params, method_text, dict_link) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (callee_method_sig[0], callee_class_name, callee_method_name, callee_return_type, callee_params, callee_method_sig[1], callee_dict_link) )
                connection.commit()
            #-------Interface insertion--------#
            interface_text = getInterfaceText(caller_method_sig[1], val)  # call to data_collection.py
            if len(interface_text) == 0 :  # if we don't any out put
                interface_text = "No interface text found, refer to method text below, and/or docs."
            elif len(interface_text) > 0:  # if there are 1 or more lines of output join them on '\n' for insert into the sheet
                interface_text = '\n'.join(interface_text)

            return_text = getReturnText(callee_method_sig)  # another call to data_collection.py to get the return text from the callee text

            crsr.execute( "INSERT INTO interfaces (interface_text, return_text, caller_signature, callee_signature, caller_class, callee_class, caller_return_type, callee_return_type, caller_method_name, callee_method_name, caller_params, callee_params, caller_dict_link, callee_dict_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (str(interface_text), return_text, caller_method_sig[0],
            callee_method_sig[0], caller_class_name, callee_class_name, caller_return_type, callee_return_type,
            caller_method_name, callee_method_name, caller_params, callee_params, caller_dict_link, callee_dict_link))
            connection.commit()  # insert into interfaces DB information on each interface between the caller and callees

    sys.stdout.write('\r')
    sys.stdout.write("Collecting and Inserting Data [%-50s]" % ('='*50))
    sys.stdout.flush()  # fully populate the loading bar to indicate the data insertion finished
    print("\nTables populated...")
    # now we have to recompile the interface graph from the database, because there is a chance that
    # when we were initially compiling the interface graph we skipped over branches that had already been traversed
    # in previous script executions. So remake the graph from scratch now that all the new data is inserted
    interface_graph = createInterfaceGraphFromDB(start_func, start_func_dict_link, crsr)

sorted_list = topological(interface_graph) # top sort the interface graph

print("Methods sorted topologically...")

def updateGlobalVarsModded():
    """
    Method that updates the methods table to include the the global variables that were modded by each method
    discovered in the interface graph we compiled
    """
    glbl_connection = sql.connect("globals.db")
    # cursor
    glbl_crsr = glbl_connection.cursor() # connect to globals.db
    for method in sorted_list:
        # loop through the sorted_list and for every method first select the list of globals affected by that method
        # stored in the globals.db file, and then insert that list into the methods table in the global_vars_modded column
        glbl_crsr.execute('SELECT var_name FROM globals WHERE method_used = ?', (method.split('#')[0],))
        res = glbl_crsr.fetchall()
        if len(res) > 0:
            # if statements to break up the method into the proper pieces for the update statement
            method = method.split('::')
            if len(method) == 1:
                cn = 'Unknown'
                tmp = method[0].split('#')
                mn = tmp[0].strip()
                dl = tmp[1].strip()
            else:
                cn = method[0].strip()
                tmp = method[len(method)-1].split('#')
                dl = tmp[1].strip()
                mn = '::'.join(method[1:])
                mn = mn[:mn.find('#')]
            crsr.execute("UPDATE methods SET global_vars_modded = ? WHERE class_name = ? AND method_name = ? AND dict_link = ?",
            (str(res), cn, mn, dl,)) # update methods table

if USE_GLOBALS:  # if the user chose to use globals for this chart then we will update global vars modded column
    updateGlobalVarsModded()
    print("Global variable interfaces updated...")

#--------------------------------End of db creation-----------------------------#
# to get the method signatures in order, select statement for top_seq_num 1-size where
# curr num = top_seq_num
# for this section we want to compile the "full_sorted_list" instead of the 'sorted_list'
# because the full sorted list contains the full method signatures of the methods, without their
# dict_link for insert into the excel sheet. For this we use the method name and dict link from the
# entries in "sorted list"
get_current_method = "SELECT method_signature FROM methods WHERE class_name = ? AND method_name = ? AND dict_link = ?"
full_sorted_list = []
for i in sorted_list:
    # iterate through the methods and break them up into pieces for the select statement
    if "::" in i:
        method = i.split('::')
        cn = method[0].strip()
        tmp = method[len(method)-1].split('#')
        dl = tmp[1].strip()
        mn = '::'.join(method[1:])
        mn = mn[:mn.find('#')]
    else:
        cn = "Unknown"
        j = i.split('#')
        mn = j[0].strip()
        dl = j[1]
    crsr.execute(get_current_method, (cn,mn,dl))
    tmp = crsr.fetchall()
    full_sorted_list.append(tmp[0][0])  # select the method we are looking for and then append it to the list

#------------------------------Generation of N2 Excel Sheet--------------------#
# this section is just a series of select statements and inserts into the excel sheet
# a lot of the statements in here are just specific to the format or way that the sheet is laid out

if os.path.isfile('n2_chart.xlsx'): # check again if the excel sheet is open and ensure that the person closes it before it moves on
    try:
        excel_sheet = open('n2_chart.xlsx', 'r+')
    except:
        print('\nPlease close or move the file \'n2_chart.xlsx\' in this directory before proceeding. Press enter to continue')
        input()
    excel_sheet.close()

# initialize file
workbook = xlsx.Workbook('n2_chart.xlsx')
worksheet = workbook.add_worksheet()

#create topics and function/method column headers
h1 = workbook.add_format({'bold' : True, 'font_size' : 14})
worksheet.write('A1', "Topic", h1)
worksheet.set_column(0, 0, 15)
h2 = workbook.add_format({'bold' : True, 'font_size' : 11, 'bg_color' : '#DFDFA0', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'})
worksheet.write('B2', "Function / Method", h2)
worksheet.set_column(2, 1, 50)
worksheet.set_row(1, 50)
worksheet.write_blank('B1', None, workbook.add_format({'bg_color' : '#DFDFA0' }))
worksheet.write_blank('B3', None, workbook.add_format({'bg_color' : '#DFDFA0' }))
worksheet.set_row(1, 80)
worksheet.set_row(2, 40)

# list of colors for the excel sheet to choose from as it generates the diagonal
class_colors = [ '#FF9999', '#FFCC99', '#FFFF99', '#CCFF99', '#99FF99', '#99FFCC', '#99FFFF', '#99CCFF', '#9999FF', '#CC99FF', '#FF99FF', '#FF99CC', '#FF0000', '#FF3333', '#FF9933', '#FFFF33', '#99FF33',
'#33FF33', '#33FF99','#33FFFF', '#3399FF', '#3333FF', '#9933FF', '#FF33FF', '#FF3399', '#CC0000', '#CC6600', '#CCCC00','#66CC00', '#00CC00', '#00CC66', '#00CCCC', '#0066CC', '#0000CC', '#6600CC', '#CC00CC',
'#CC0066','#660000', '#663300', '#666600', '#336600', '#006666', '#003366', '#660066', '#660033' ]
no_class_color = "#C0C0C0"  # default grey color for when there is no class specified
current_classes = []

#----------------------
# Terminology
# sorted_list = sorted list of <ClassName>::<MethodName>
# full_sorted_list = sorted list of full method signature
#----------------------
# populate the left justified function/method column
col = 1
row = 3
count = 0
for method in full_sorted_list:
    if "::" in sorted_list[count]:
        curr_class = sorted_list[count].split('::')[0].strip()
        if curr_class not in current_classes:
            current_classes.append(curr_class)
        cell_color = class_colors[current_classes.index(curr_class)%len(class_colors)]
    else:
        cell_color = no_class_color

    method_cell_format = workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : cell_color })
    worksheet.write( row, col, method, method_cell_format )
    worksheet.set_row(row, 80)
    row+=1
    count+=1

#column for global vars used
# for i in range(0, len(full_sorted_list)+4 ):
#     worksheet.write_blank("C"+str(i), None, workbook.add_format({'bg_color' : '#EBEBEB', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top' }))
worksheet.set_column('C:C', 25, workbook.add_format({'bg_color' : '#EBEBEB', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top' }))
worksheet.write('C3', 'Attributes Used / Attributes Set', workbook.add_format({'bg_color' : '#EBEBEB','bold' : True, 'font_size' : 11, 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))
for i in range(3, 3+len(full_sorted_list)):
    worksheet.write_blank(2, i, None, workbook.add_format({'bg_color' : '#EBEBEB', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top' }))

#row for top justified method signatures
row = 1
col = 3
count = 0
for method in full_sorted_list:
    if "::" in sorted_list[count]:
        curr_class = sorted_list[count].split('::')[0].strip()
        if curr_class not in current_classes:
            current_classes.append(curr_class)
        cell_color = class_colors[current_classes.index(curr_class)%len(class_colors)]
    else:
        cell_color = no_class_color

    method_cell_format = workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : cell_color })
    worksheet.write( row, col, method, method_cell_format )
    worksheet.set_column(row, col, 50)
    col+=1
    count+=1

# inserting the diagonals
col = 3
row = 3
count = 0
for method in full_sorted_list:
    if "::" in sorted_list[count]:
        curr_class = sorted_list[count].split('::')[0].strip()
        if curr_class not in current_classes:
            current_classes.append(curr_class)
        cell_color = class_colors[current_classes.index(curr_class)%len(class_colors)]
    else:
        cell_color = no_class_color
    method_cell_format = workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : cell_color })
    worksheet.write( row, col, method, method_cell_format )
    row+=1
    col+=1
    count+=1

# inserting global vars at the top
obj_rollup = []
for i in range(0, len(full_sorted_list)):
    crsr.execute("SELECT global_vars_modded FROM methods WHERE method_signature = ?", (full_sorted_list[i],))
    res = crsr.fetchall()
    if len(res) > 0 and res[0][0] != None:
        res = str(res[0])
        for ch in ['(', ')', '\'', '\"', '[', ']']:  # format the list of global variables
            if ch in res:
                res = res.replace(ch, '')
        res = res.replace(',,', ', ')
        obj_rollup.append(res)
        worksheet.write(i+3, 2, res, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : '#EBEBEB' }))
        worksheet.write( 2, i+3, res, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : '#EBEBEB' }) )
    else:
        obj_rollup.append('+') #sentinel value to indicate no obj use

# adding the rows at the very bottom to contain information
worksheet.set_row(len(full_sorted_list)+3, 15, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : '#D9D9D9', 'top' : 6}) )
worksheet.write(len(full_sorted_list)+3, 2, 'Function/Method Text', workbook.add_format({'bold' : True, 'bg_color' : '#D9D9D9', 'top' : 6, 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))

worksheet.set_row(len(full_sorted_list)+4, 15, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : '#C0C0C0'}) )
worksheet.write(len(full_sorted_list)+4, 2, 'Called By', workbook.add_format({'bold' : True, 'bg_color' : '#C0C0C0', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'top' : 1}))

worksheet.set_row(len(full_sorted_list)+5, 15, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : '#D9D9D9', 'top' : 1, 'bottom' : 1}) )
worksheet.write(len(full_sorted_list)+5, 2, 'Functions Called', workbook.add_format({'bold' : True, 'bg_color' : '#D9D9D9', 'top' : 1, 'bottom' : 1, 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))

worksheet.set_row(len(full_sorted_list)+6, 15, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : '#D9D9D9', 'bottom' : 1}) )
worksheet.write(len(full_sorted_list)+6, 2, 'Global/Public Object Rollup', workbook.add_format({'bold': True, 'bg_color' : '#D9D9D9', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bottom' : 1}))
# insert the obj rollup at the bottom of the sheet
curr_rollup = ''
for i in range(0, len(obj_rollup)):
    if obj_rollup[i] != '+':
        tmp = str(obj_rollup[i:])
        tmp = tmp.replace('\'+\', ', '')
        curr_rollup = tmp
        worksheet.write(len(full_sorted_list)+6, i+3, tmp, workbook.add_format({'bg_color' : '#D9D9D9', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bottom' : 1}))
    else:
        worksheet.write(len(full_sorted_list)+6, i+3, curr_rollup, workbook.add_format({'bg_color' : '#D9D9D9', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bottom' : 1}))

worksheet.set_row(len(full_sorted_list)+7, 15, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bottom' : 1}) )
worksheet.write(len(full_sorted_list)+7, 2, 'Remarks', workbook.add_format({'bold' : True, 'bg_color' : '#EBEBEB', 'bottom' : 1, 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))
worksheet.write_blank(len(full_sorted_list)+7, 1, None, workbook.add_format({'border' : 0}))
worksheet.write_blank(len(full_sorted_list)+7, 0, None, workbook.add_format({'border' : 0}))

worksheet.set_row(len(full_sorted_list)+8, 15, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}) )
worksheet.write(len(full_sorted_list)+8, 2, 'Analysis', workbook.add_format({'bold' : True, 'bg_color' : '#EBEBEB', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))

worksheet.set_row(len(full_sorted_list)+9, 15, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}) )
worksheet.write(len(full_sorted_list)+9, 2, 'Error / Off-Nominal / Risk', workbook.add_format({'bold' : True, 'bg_color' : '#EBEBEB', 'top' : 1, 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))

worksheet.set_row(len(full_sorted_list)+10, 15, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}) )
worksheet.write(len(full_sorted_list)+10, 2, 'Requirement', workbook.add_format({'bold' : True, 'bg_color' : '#EBEBEB', 'top' : 1, 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))

# freeze panes
worksheet.freeze_panes('D4')

# now insert the interface text and return text in the right place
# use full_sorted_list, the location of the method in the
for i in range(0, len(full_sorted_list)):
    crsr.execute("SELECT interface_text, return_text, callee_signature FROM interfaces WHERE caller_signature = ?",
    (full_sorted_list[i],))
    curr_interfaces = crsr.fetchall()
    if len(curr_interfaces) != 0:
        for interface in curr_interfaces:
            callee_offset = list(full_sorted_list).index(interface[2])
            worksheet.write(i+3, callee_offset+3, interface[0], workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))
            worksheet.write(callee_offset+3, i+3, interface[1], workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}))

# insert the method text, called by, functions called rows at the bottom
count = 0
get_method_text = "SELECT method_text FROM methods WHERE method_signature = ?"
get_called_by = "SELECT caller_class, caller_method_name FROM interfaces WHERE callee_signature = ?"
get_funcs_called = "SELECT callee_class, callee_method_name FROM interfaces WHERE caller_signature= ?"
for method in full_sorted_list:
    crsr.execute(get_method_text, (method,))
    tmp = crsr.fetchall()
    tmp = tmp[0][0]
    worksheet.write(len(full_sorted_list)+3, count + 3, tmp, workbook.add_format({'text_wrap' : True, 'align' : 'left', 'valign' : 'top', 'bg_color' : '#D9D9D9', 'top' : 6}) )

    crsr.execute(get_called_by, (method,))
    tmp = crsr.fetchall()
    called_by = []
    if len(tmp) > 0:
        for tuple in tmp:
            if tuple[0] == 'Unknown':
                if tuple[1] not in called_by:
                    called_by.append(tuple[1])
            else:
                tmp2 = tuple[0] + '::' + tuple[1]
                if tmp2 not in called_by:
                    called_by.append(tuple[0] + '::' + tuple[1])
    else:
        called_by = 'None in this graph'
    worksheet.write(len(full_sorted_list)+4, count + 3, str(called_by), workbook.add_format({'bg_color' : '#C0C0C0', 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}) )

    crsr.execute(get_funcs_called, (method,))
    tmp = crsr.fetchall()
    called = []
    if len(tmp) > 0:
        for tuple in tmp:
            if tuple[0] == 'Unknown':
                if tuple[1] not in called:
                    called.append(tuple[1])
            else:
                tmp2 = tuple[0] + '::' + tuple[1]
                if tmp2 not in called:
                    called.append(tuple[0] + '::' + tuple[1])
    else:
        called = 'None in this graph'
    worksheet.write(len(full_sorted_list)+5, count + 3, str(called), workbook.add_format({'bg_color' : '#D9D9D9', 'top' : 1, 'bottom' : 1, 'text_wrap' : True, 'align' : 'left', 'valign' : 'top'}) )

    count+=1


workbook.close()
# save all changes made
connection.commit()
# finished
connection.close()
print( "\nN2 Chart created"  )
exit()
