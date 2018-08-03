import sqlite3 as sql
import os
from bs4 import BeautifulSoup
import re


def collectGlobals(folder_path):
    """
    Method to get all of the global and public objects from the understand docs
    It uses the the object cross reference pages of the understand docs

    """
    print("Collecting global/public objects from this project...")
    glbl_connection = sql.connect("globals.db") #creates a globals.db file
    glbl_crsr = glbl_connection.cursor() #crsr to execute commands

    create_globals_table = """CREATE TABLE globals (
        global_id INTEGER PRIMARY KEY,
        var_name VARCHAR(255),
        method_used VARCHAR(200), /* the method signature of where it was used */
        use_loc VARCHAR(255) /* line where it was used */
        );"""
    glbl_crsr.execute(create_globals_table) #inline sql to create table for objects

    ref_page = 'Non-Alpha'
    count = 0
    #---regex compiles----#
    # stops the code from recompiling the regex and adding it to the cache every loop
    global_regex = '.+Global Object\)' #regex to search for the objs labeled public/global
    global_regex = re.compile(global_regex)
    public_regex = '.+Public Object\)'
    public_regex = re.compile(public_regex)
    static_remove = re.compile('   \(Static')
    use_search = re.compile(' Use ')
    set_search = re.compile(' Set ')
    #---------------------#
    while ref_page == 'Non-Alpha' or ( ord(ref_page) <= ord('Z') ) :  # loop to loop through each of the pages for the variables
        print("Collecting global variables that start with ", ref_page, "...")
        objxref_html = open(folder_path + '\object_xref_' + ref_page + '.html')
        objxref_html = BeautifulSoup(objxref_html, 'html.parser')  # get the page's html in a parsable object
        obj_blocks = str(objxref_html).split('\n\n') # break the page into units for each object
        for block in obj_blocks:
            matched = False
            if global_regex.search(block.split('\n')[0]):
                obj = 'Global'
                matched = True
            elif public_regex.search(block.split('\n')[0]):
                obj = 'Public'
                matched = True
            if matched: #if the block has been identified as public/global object
                block_txt = BeautifulSoup(block, 'html.parser').getText()
                block_txt = block_txt.split('\n')
                tmp = block_txt[0].split('%s Object)  Declared as: ' % obj) #split up the first line's information

                if len(tmp) > 1: #there is a Declared as:
                    var_name = tmp[1].strip() + "   " + tmp[0].strip()
                else: # no Declared as
                    var_name = tmp[0].split()[0].strip()
                if static_remove.search(var_name):  #get rid of the static part if it's there
                    var_name = var_name[:-8].strip()
                elif '(' in var_name:
                    var_name = var_name[:-2].strip()
                used_in_methods = {}  # now search the next lines of the block to find which methods the obj is used in
                for line in block_txt[1:]:
                    if(use_search.search(line)) or (set_search.search(line)):
                        line = line.split()
                        use_loc = line[-3] + " " + line[-2]
                        method_used = line[-1].strip()
                        if method_used not in used_in_methods:  #for the case where there are multiple lines in one method
                            used_in_methods[method_used] = [use_loc] # where the obj is used method = key, lines used = val
                        else:
                            used_in_methods[method_used].append(use_loc)
                if len(used_in_methods) > 0:
                    for method in used_in_methods: # if there were places where the obj was used insert into the db
                        glbl_crsr.execute('INSERT INTO globals (global_id, var_name, method_used, use_loc) VALUES (?, ?, ?, ?)',
                         (count, var_name, method, str(used_in_methods[method]), ))
                        count += 1

        if ref_page == 'Non-Alpha':
            ref_page = 'A'
        else:
            ref_page = chr(ord(ref_page)+1)
    # save all changes made
    glbl_connection.commit()
    # finished
    glbl_connection.close()

#collectGlobals("C:\\Users\\sspelsbe\\28d_html")
