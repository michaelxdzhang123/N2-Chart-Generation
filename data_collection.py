import sqlite3 as sql
import os
from bs4 import BeautifulSoup
import re
from regexMethodSignatures import regexClassName, regexParams, regexMethodName, regexReturnTypes
from collect_globals import collectGlobals
from create_tables import createTables, globalsTable
from time import sleep
import sys
import webbrowser


#-----------------Data collection methods-----------------#
# These methods are the most important parts of the script, they actually
# retrieve the interface trees as well as the method text and method signatures

def classInDB(class_name, interface_db_cursor):
    crsr = interface_db_cursor
    crsr.execute("SELECT class_name FROM classes WHERE class_name = ?", (class_name,))
    res = crsr.fetchall()
    if len(res) > 0:
        return True
    else:
        return False


# VOCAB: dict_link are dictionary links. In the data dictionary every object from parameters to program blocks
#        have a unqiue number sequence associated with them and it is accessible from the html of the object
#  ex: <a name="30302"> </a><b>U</b>   (Local Object)<a href="object_xref_U.html#30302">[xref]</a>
#              [<a href="30152.html#1591">NVA_CLEKF_Process_Opt_MR.cpp, 1591</a>]
# 1591 would be the dict_link for this object 'U'. These numbers are used to identify overloaded methods unqiuely

# returns [Boolean if its there, dict_link]
def methodInDB(method_name, dict_link, interface_db_cursor):  #checks the database to see if the method exists already
    """
    Method used to check the database to see if a method exists in the database
    returns a list [Boolean True/False of if the method exists in the db, dictionary link/ID]
    """
    crsr = interface_db_cursor
    #splitting method into parts
    if "::" in method_name:
        method = method_name.split('::')
        cn = method[0].strip()
        mn = '::'.join(method[1:]).strip()
    else:
        cn = "Unknown"
        mn = method_name
    if dict_link == '':  #dict link should only be empty on the initial call
        # search for any method with the same name and class
        crsr.execute("SELECT class_name, method_name, method_text, dict_link FROM methods WHERE class_name = ? AND method_name = ?", (cn, mn))
        res = crsr.fetchall()
        if len(res) == 0:   #method not in table
            return [False, '']
        else:  # found something, verify it is right
            if len(res) == 1:
                print('Method found in database.')
                if res[0][0] == 'Unknown':
                    print(res[0][1])
                else:
                    print('::'.join(res[0][0:2]))
                print(res[0][2])
                print('Is this the correct method? (Y/N)') #prompt the user to confirm that this is the right method
                k = input()
                k = k.strip()
                while( k not in ['N', 'n', 'Y', 'y' ] ):
                    print('Invalid input, try again')
                    k = input()
                if k == 'Y' or k == 'y':
                    return [True, res[0][3]]
                elif k == 'N' or k == 'n':
                    return [False, '']
            elif len(res) > 1:
                print("\nMethod found in database")
                count = 1
                for r in res:
                    tmp = str(count) + ': '
                    print(tmp)
                    if r[0] == 'Unknown':
                        print(r[1])
                    else:
                        print('::'.join(r[0:2]))
                    print(r[2],'\n')
                    count += 1
                print('Which one of these is the correct method?\nPut 0 for none of them.') #if there are multiple versions of the method in the db
                # prompt the user to select which method is the right method, prints the method text
                k = input()
                try: k = int(k)
                except: k = -1
                while( int(k) > len(res) or int(k) < 0  ):
                    print("Invalid input: try again please")
                    k = input()
                    try: k = int(k)
                    except: k = -1
                if k == 0:
                    return [False, '']
                elif k > 0 and k <= len(res):
                    return [True, res[k-1][3]]
    else:  #there is a dict_link, can check for exact, usually what happens
        crsr.execute("SELECT class_name, method_name FROM methods WHERE class_name = ? AND method_name = ? AND dict_link = ?", (cn, mn, dict_link))
        #simple sql select
        res = crsr.fetchall()
        if len(res) == 0:   #method not in table
            return [False, dict_link]
        elif len(res) > 0:  # we found something
            return [True, dict_link]


def createInterfaceGraphFromReport(method_name, folder_path, crsr):
    """
    Initial function called when creating interface graph from reports, calls the method getInterfacesFromReport
    that calls itself recursively. It sets up global variables that getInterfacesFromReport updates.
    """
    ######
    # Cycle log file: this .txt file will be here to capture any time the code captures a cycle in the graph
    global cycles_log
    cycles_log = open('cycles.txt', "w")
    ######
    # This variable is used to autoselect '0' for each time when the code prompts you to pick a constructor
    # THIS IS A SPECIAL CASE, the code will prompt the user when the invocation tree of a method contains a constructor
    # and then this script searches for the invocation tree of that constructor and it finds multiple versions of
    # the constructor documented. If skip duplicates = True then the script will not make the user pick and it won't
    # go any further down the invocation branch to search for interfaces stemming off of that constructor.
    global SKIP_DUPLICATES
    ######
    print("Given method not in database, collecting interfaces from reports.")
    print('Would you like to automatically skip identified duplicates? (Y/N)' )
    k = input()
    k = k.strip()
    while( k not in ['N', 'n', 'Y', 'y' ] ):
        print('Invalid input, try again')
        k = input()
    if k == 'y' or k == 'Y':
        print("Ok, will skip duplicates")
        SKIP_DUPLICATES = True
    elif k == 'n' or k == 'N':
        print("Ok, will prompt you")
        SKIP_DUPLICATES = False
    global interface_graph #graph of interfaces
    global start_func_dict_link  #the dict link of the first function passed in
    interface_graph = {}
    start_func_dict_link = ['']
    global loading_count # for the little loading bar animation
    loading_count = [0]
    getInterfacesFromReport( method_name, '', folder_path, crsr, '')
    cycles_log.close()
    return interface_graph, start_func_dict_link


#dict_link = the link to the methods def in the data dictionary
def getInterfacesFromReport( method_name, dict_link, folder_path, crsr, caller):
    """
    This method recursively discovers all of the branches of invocation stemming off of the initial
    function passed into the script. It checks for cycles in the graph.
    """
    if loading_count[0] > 50:
        loading_count[0] = 0
    sys.stdout.write('\r')
    sys.stdout.write("Generating Interface Graph [%-50s]" % ('='*loading_count[0]))
    sys.stdout.flush() #loading bar print for the console
    loading_count[0] += 1
    if len(method_name) < 1: # edge case calls empty name
        return
    test_if_in_graph = method_name + "#" + dict_link
    if test_if_in_graph in interface_graph: # how to check for cycles and recursion
        print('\nWARNING: Possible cycle found in invocation tree. %s was invoked by %s and is already a vertx in the interface graph.' % (method_name, caller), file = cycles_log)
        return
    if not method_name[0].isalpha():
        frst = 'Non-Alpha'
    else:
        frst = method_name[0]  # decide which char to use for inv tree file
    try:
        invtrees_html = open(folder_path + '\simpleinvtree_' + frst + '.html', encoding='utf8')
    except FileNotFoundError as e: #if there is a failure to open the file
        return
    invtrees_html = BeautifulSoup(invtrees_html, 'html.parser')
    invtree_blocks = str(invtrees_html).split("\n\n") #break the whole page into individual trees
    inv_list_text = [] #will contain the current invocation tree

    # Below is to see if the method is a constructor. This important because in Understand docs the
    # way that it links the constructor to its place in the data dictionary changes
    # depending on whether the constructor is being called or is the caller (Frustrating!), making it impossible to
    # automatically match the constructor tree from where it is being called to its tree automatically,
    # which is what prompts the user input when duplicates are discovered.
    test_for_constructor = method_name.split('::')
    if len(test_for_constructor) < 2:
        isConstructor = False
    else:
        if test_for_constructor[0].strip() == test_for_constructor[1].strip():
            isConstructor = True
        else:
            isConstructor = False
    if dict_link == '' or isConstructor:
        inv_lists = []  #This list will store all of the invocation trees that the script finds that come from the same Class::Method
    #-----regex compilation-----#
    get_link_regex = re.compile(r'\<a href=\"dictionary_.+?\.html#(.+)\"\>')
    #---------------------------#
    for tree in invtree_blocks: #search for the right tree
        original_block = tree
        tree = BeautifulSoup(tree, 'html.parser')
        tree = str(tree).replace("|", "") # take out the | symbol understand puts in the html
        tree = tree.split('\n') # change the tree into a list where [0] == invoker and [1:] are the invocations
        tree = list(map(str.strip, tree)) # strip each of the strings in the list
        invoker_html = tree[0]  # still in HTML
        invoker_text = BeautifulSoup(invoker_html, 'html.parser')
        invoker_text = invoker_text.get_text() # turn to text
        if invoker_text == method_name:  #found a potentially correct tree
            if dict_link == '' or isConstructor:
                inv_lists.append(original_block)  #collect potential lists
                continue
            else:  # normal behavior
                tmp_link = get_link_regex.search(invoker_html).group(1) # get the dictionary link
                if tmp_link == dict_link: # we have the right name and dict_link
                    inv_list_text.append(invoker_text + '#' + tmp_link)
                    for index in range(1, len(tree)): #loop through the tree and turn the HTML to text and add to inv_list_text
                        tmp_link = get_link_regex.search(tree[index])
                        method_text = BeautifulSoup(tree[index], 'html.parser')
                        method_text = method_text.get_text()
                        if tmp_link == None and method_text == '': # this if statement is to capture when the invocation tree is at the bottom of the page so the .split '\n\n' didn't work
                            #handle when it as at the end of the page
                            table_text = BeautifulSoup(tree[index+1], 'html.parser')
                            table_text = table_text.get_text()
                            if table_text == 'Non-AlphaABCDEFGHIJKLMNOPQRSTUVWXYZ': #search for table at the bottom of the page
                                break
                        inv_list_text.append(method_text + '#' + tmp_link.group(1))
                    break # found the right tree so we can stop iterating over them
#---------------Handling first time methods------------------#
    if dict_link == '':  # this block is for when the method is passed in at the start of the code, so no dict link
        if dict_link == '' and len(inv_lists) == 0:  #no invocations found
            print( "\n\nThis function doesn't have any interfaces! Try a different one.") # user gave a function without interfaces
            exit()
        if dict_link == '' and len(inv_lists) == 1: # we found an invocation tree that matches the name, assume it is right
            inv_list_html = inv_lists[0]
            inv_list_html = str(inv_list_html).split('\n')
        elif dict_link == '' and len(inv_lists) > 1:  #more than one, no html link to ref yet, have to get user input to decide
            # prompt user to tell me which one they want
            count = 0
            for tree in inv_lists: #print out each of the method's inv trees and ask which is the right one
                count += 1
                tree_text = BeautifulSoup(tree, 'html.parser')
                tree_text = tree_text.get_text()
                tmp = str(count) + ": "
                print(tmp)
                print(tree_text, '\n')
                start_letter = tree_text[0]
            # open the inv tree understand html page so the user can have some help deciding
            webbrowser.open('file://' + os.path.realpath(folder_path + '\simpleinvtree_' + frst + '.html'))
            print('\n\nMultiple invocation trees with same Class::Method found. Which one would you like to generate a chart with?')
            print('Type the number of the tree you would like to start with.\nI have opened the HTML report in your browser as well to help you decide.')
            k = input() #have the user select a number
            try: k = int(k)
            except: k = -1
            while( int(k) > count or int(k) < 1  ): #make sure it is a good input
                print("Invalid input: try again please")
                k = input()
                try: k = int(k)
                except: k = -1
            inv_list_html = inv_lists[k-1] # we now know which one we want
            inv_list_html = str(inv_list_html).split('\n') # list of methods with link wrapping it in html
        if dict_link == '' and len(inv_list_html) > 0: # if inv_list_html len is > 0 then we found something, manipulate it for recursion
            inv_list_text = []
            count = 0
            for method in inv_list_html:
                method_link = get_link_regex.search(method).group(1)
                method_text = BeautifulSoup(method, 'html.parser')
                method_text = method_text.get_text() #turn from HTML to text
                if count > 0: #methods other than the invoker have these | that understand puts
                    method_text = method_text.replace('| ', '')
                if count == 0: # since the first method that is passed in by the user doesn't have a dict_link we must save it
                    start_func_dict_link[0] = method_link
                method_string = method_text + "#" + method_link
                inv_list_text.append(method_string) #get the tree in list form for recursion
                count += 1
#------------Handling when the constructor has a different dict link----------------#
    else:
        if isConstructor and len(inv_lists) == 0: # there was no invocation tree found
            return
        if isConstructor and len(inv_lists) == 1: # only one found, this must be the correct one, assume it is correct
            # have the update dict link on the interface graph to this new one
            # use this as the invocation tree
            inv_list_html = inv_lists[0]
            inv_list_html = str(inv_list_html).split('\n')
        elif isConstructor and len(inv_lists) > 1:
            # when the constructor has many definitions, make the user select the one we want
            if SKIP_DUPLICATES: return #this is for when the user selects they don't want to be prompted to select the right constructor
            count = 0
            for tree in inv_lists:  #print out the inv trees and open the web browser to help the user choose the right one
                count += 1
                tree_text = BeautifulSoup(tree, 'html.parser')
                tree_text = tree_text.get_text()
                tmp = str(count) + ": "
                print(tmp)
                print(tree_text, '\n')
                start_letter = tree_text[0]
            webbrowser.open('file://' + os.path.realpath(folder_path + '\simpleinvtree_' + frst + '.html'))
            print('\n\nMultiple versions of the same constructor found. Which one is called by', caller, '?')
            print('Type the number of the correct tree.\nI have opened the HTML report in your browser as well to help you decide.\nIf you don\'t wish to decide, type \'0\'')
            k = input()
            try: k = int(k)
            except: k = -1
            while( int(k) > count or int(k) < 0  ):
                print("Invalid input: try again please")
                k = input()
                try: k = int(k)
                except: k = -1
            if k == 0:  #if the user selects 0, it won't continue traversing this branch
                return
            inv_list_html = inv_lists[k-1] # we now know which one we want
            inv_list_html = str(inv_list_html).split('\n') # list of methods with link wrapping it in html
        # get html into neat list
        if isConstructor and len(inv_list_html) > 0: # if inv_list_html len is > 0 then we found something, manipulate it for recursion
            inv_list_text = []
            for i in range(0, len(inv_list_html)): #iterate through the tree and get it in proper text format with dict_link
                method_link = get_link_regex.search(inv_list_html[i]).group(1)
                method_text = BeautifulSoup(inv_list_html[i], 'html.parser')
                method_text = method_text.get_text()
                if i > 0:
                    method_text = method_text.replace('| ', '')
                method_string = method_text + "#" + method_link
                if i == 0 : # have to update the graph last call with the new dict link, because of the issue with the dict link being different when it is the callee vs. the caller
                    old_string = method_name + '#' + dict_link # string to be replaced
                    prev_tree = interface_graph[caller]
                    prev_tree[prev_tree.index(old_string)] = method_string
                    interface_graph[caller] = prev_tree
                inv_list_text.append(method_string)
    #-----------Ready to fix the correct invocation list up for insert into graph----#
    # when we get here we have inv_list_text with the list of invocations in order inv_list_text[0] == invoker and [1:] invocations
    if len(inv_list_text) >= 2:  # there are invoked methods
        if inv_list_text[0] not in interface_graph:  # double check to make sure there won't be a cycle created
            i = 1
            while i < len(inv_list_text):
                if '(Virtual)' in inv_list_text[i]: #if virtual is on there strip it off for the graph
                    inv_list_text[i] = inv_list_text[i].replace('  (Virtual)', '').strip()
                if inv_list_text[i] in interface_graph or inv_list_text[i] == inv_list_text[0] : #deal with cycles caused by recursion or edges
                    # outputs to log file. This case will be triggered if a method exists in the current invocation tree and it has
                    # already been added to the graph as another vertex. This maintains integrity of acyclic quality for topological sort
                    print('\nWARNING: Possible cycle found in invocation tree. %s was invoked by %s, and is already a vertx in the interface graph.' % (inv_list_text[i], inv_list_text[0]), file = cycles_log)
                    # warning to the user
                    del inv_list_text[i] # delete the edge causing the cycle for the sake of the topological sort
                    i -= 1
                i += 1
            if len(inv_list_text) >= 2: # after del edges that make cycles make sure there at least one edge coming from the vertex
                interface_graph[inv_list_text[0]] = inv_list_text[1:]
            else:
                return
        else: # this only gets triggered if the dict_link of the invoker method changed between the start of this method's execution and here
            print('\nWARNING: Possible cycle found in invocation tree. %s was invoked by %s and is already a vertx in the interface graph.' % (inv_list_text[0], caller), file = cycles_log)
            return
    for i in range(1, len(inv_list_text)):  #time to recurse over the branches left in the tree
        tmp = inv_list_text[i].split('#') # break the method from its dict link
        method_name = tmp[0]
        dict_link = tmp[1]
        # first check if the method is in the DB, if it is we assume that that the branch from that method has been fully traversed
        if not methodInDB(method_name, dict_link, crsr)[0]:
            getInterfacesFromReport(method_name, dict_link, folder_path, crsr, inv_list_text[0])  # calls getInt. on next method



def createInterfaceGraphFromDB(method_name, dict_link, interface_db_cursor):
    """
    When the method passed in to the script is in the database we can recreate the interface using SQL select statements
    """
    crsr = interface_db_cursor
    global interface_graph
    interface_graph = {}
    getInterfacesFromDB( method_name, dict_link, crsr )
    return interface_graph


def getInterfacesFromDB( method_name, dict_link, crsr ):
    """
    Recursive method to create the interface graph using inline SQL
    """
    if "::" in method_name:  # break the method into pieces for the query
        method = method_name.split('::')
        cn = method[0].strip()
        mn = '::'.join(method[1:]).strip()
    else:
        cn = "Unknown"
        mn = method_name
    # SQL statement to get all of the invoked methods from the caller currently passed in, basically recreating an invocation tree
    crsr.execute("SELECT callee_class, callee_method_name, callee_dict_link FROM interfaces WHERE caller_class = ? AND caller_method_name = ? and caller_dict_link = ?", (cn, mn, dict_link ))
    res = crsr.fetchall()
    if len(res) == 0: # if there was nothing there
        return
    method_name = method_name + '#' + dict_link
    interface_graph[method_name] = [] # we assume there won't be any cycles in the graph because when it was made from reports it took care of cycles
    for i in res:
        if i[0] == 'Unknown': # build the method together for the interface graph
            j = i[1]
            tmp = j + '#' + i[2]
        else:
            j = "::".join(i[0:2])
            tmp = j + '#' + i[2]
        interface_graph[method_name].append(tmp)
        getInterfacesFromDB( j, i[2], crsr )  #recursive call to continue building the tree




def getMethodSignature(method_name, folder_path):
    """
    Method that gets the method signature and method text from the actual
     .cpp and .h files in the FSW from links in the data dictionary.
     Opens the data dictionary file and then parses the .cpp or .h file for the method
    """
    if len(method_name) == 0: # some case where we get an empty method_name
        return ['','']
    if '(Virtual)' in method_name:  # if, for some reason there is still virtual in the method name, remove it
        method_name = method_name[:-10].strip()
    if not method_name[0].isalpha():  # account for non alpha starting methods
        first = 'Non-Alpha'
    else:
        first = method_name[0]

    tmp = method_name.split('#')
    method_name = tmp[0].strip()
    dict_link = tmp[1].strip()
    dict_html = open(folder_path + '\dictionary_' + first + '.html', encoding='utf8') #open the correct data dictionary file
    dict_html = BeautifulSoup(dict_html, 'html.parser')
    # use regex to detect the correct block in the data dictionary, using the unqiue data dictionary link described above
    regex_func_html_block = re.compile(r'<a name=\"%s\">.+?\n\n' % dict_link, re.DOTALL | re.MULTILINE )
    func_html_block = regex_func_html_block.search( str(dict_html) )
    if not func_html_block:  # the regex for the correct dictionary block failed
        return [method_name, 'Could not locate definition. Please refer to the docs.']
    func_html_block = func_html_block.group()
    if 'Unknown ' in func_html_block:  # function is like memset or something built in
        return [method_name, 'Built in method. No defintion provided']
    # now search for the .cpp or .h file link
    try:
        regex_file_link = re.compile(r'<a href=\"(.+)\">')
        file_link = regex_file_link.search(func_html_block.split('\n')[1]).group(1)
    except: # no definition link found
        return [method_name, 'Could not locate definition. Please refer to the docs.']
    file_link = file_link.split('#') #the file link is formatted like: "12313.html#45" with the first number the file number and the #num the line number
    line_num = file_link[1].strip() # store line number in its own var
    #----regex compilation-----#
    regex_method_sig = re.compile( r'%s(.+[^\;])\{' % line_num, re.DOTALL | re.MULTILINE )
    regex_header = re.compile( r'%s(.+)\;' % line_num,  re.DOTALL | re.MULTILINE )
    #--------------------------#
    file_link = file_link[0].strip() # same as file_link
    def_html = open(folder_path + "\\" + file_link, encoding='utf8')
    def_lines = def_html.readlines() #open the .cpp/.h file
    inFunction = False
    method_sig = None
    method_text = ''
    bracestack = []  # initialize a stack that will determine when the method text starts and ends
    header = ''   # if this is a header and not a link to definition this will become method_sig
    header_only = '' #this string is just in case it is a header and no method definition (html)
    for line in def_lines: # go through the file looking for the right line
        if "<a name=\"%s\">" % line_num in line and not inFunction: # we are at the correcet line
            inFunction = True  # we are now "inFunction"
        if inFunction: #if we are inFunction we want to capture the text of this line
            method_text = method_text + line #initially will hold html string of the function
            header_only = header_only + line # a second variable for if the file is simply a header only declaration
        nocomment = commentRemover(line)  # remove the comments from the line temporarily for regex so it doesn't trip it
        # to convert header to text
        header_html = header_only
        header_html = BeautifulSoup(header_html, 'html.parser')
        header_html_text = header_html.get_text()
        if "{" in nocomment and inFunction:
            bracestack.append("{") #push to brace stack
            if method_sig == None: # we haven't found the method signature yet
                method_sig_html = method_text
                method_sig_html = BeautifulSoup(method_sig_html, 'html.parser')
                try: # try to regex for the method signature, if it fails pass for now
                    method_sig = regex_method_sig.search( method_sig_html.get_text() ).group(1).strip()
                    if '\n' in method_sig[1:]: #remove any trailing line #'s in header
                        inds = [ i for i, ch in enumerate(method_sig) if ch == '\n' ]
                        method_sig = list(method_sig)
                        for i in inds:
                            i += 1
                            while method_sig[i].isdigit():
                                method_sig[i] = ' '
                                i+=1
                                if i == len(method_sig):
                                    break
                        method_sig = "".join(method_sig) #method sig now doesn't have line nums if it is mutliple lines
                except:
                    pass
        if "}" in nocomment and inFunction:
            bracestack.append("}")
            if bracestack[len(bracestack)-1] == "}" and bracestack[len(bracestack)-2] == "{": #matched
                bracestack.pop() # if we have matched two braces together we can pop them off the stack
                bracestack.pop()
        if len(bracestack) == 0 and inFunction and method_sig != None: #if after we pop off the braces len == 0 and inFunction
            inFunction = False  # we know we are at the end of the function, finish this loop
            break
        #---------- for header only declarations
        # This is meant to catch the cases when the data dictionary links the script to a file
        # where ther is no method definition, but rather a headers declaration
        # this happens in .h files typically
        elif ';' in header_html_text and method_sig == None and len(header) == 0: # could be header, because no method sig found
            header = regex_header.search( header_html.get_text() )
            try:
                header = header.group(1).strip() # if we got something with regex
            except Exception as e:
                print('\n') # if the regex fails then print out the failure to the screen and continue searching
                print(e)    # ideallly this doesn't ever happen, code hasn't reached here in recent runs (07/20/18)
                print(header_html.get_text(), '\n\n')
                continue

            if '\n' in header[1:]: #remove any trailing line #'s in header
                inds = [ i for i, ch in enumerate(header) if ch == '\n' ]
                header = list(header)  # this is the same as above, remove line #'s if multiple line header
                for i in inds:
                    i += 1
                    while header[i].isdigit():
                        header[i] = ' '
                        i+=1
                        if i == len(header):
                            break
                header = "".join(header)
            break
            #----------
    method_text = BeautifulSoup(method_text, 'html.parser')  # the html we have collected in the loop for the whole method's text
    method_text = method_text.get_text() # turn it into text from HTML, will be displayed at the bottom of the excel sheet
    if header and method_sig == None: #potential its a header only declaration, in this case we didn't get any method text
        method_sig = header           # so we output a message in the excel sheete for the analyst to check the reports later
        method_text = 'Header only declaration. Check file ' + file_link + ' in the HTML reports for more information.'
    return [method_sig, method_text]

def commentRemover(text):  #credit to ChunMinChang for this method: https://gist.github.com/ChunMinChang/88bfa5842396c1fbbc5b
    """Method that will remove any C++ style comments from a string, shoutout ChunMinChang"""
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)

def getInterfaceText(caller_text, callee_method):
    """
    This method parses method text that we grabbed from getMethodSignature for
    potential interface text that is present. It makes a sort of 'best guess'
    as to which lines of the caller method text invoke the callee

    This current implementation uses only the 'in' string method to detect interfaces
    and that is why it is a 'best guess' it is by no means perfect
    """
    #pass in the caller method text and then search it for the callee method call
    callee_method = callee_method.split('#')[0].strip() # get the dict_link out
    interface_text = []
    caller_text = commentRemover(caller_text)  # don't want to trigger interface text on a comment
    caller_text = caller_text.split('\n')
    i = 0
    end_header_regex = re.compile(r'^.+?\)')
    while i < len(caller_text):   # remove method header from the interface text as to not accidentally trigger regex later
        to_remove = end_header_regex.search(caller_text[i])  #regex that searches to see the end parentheses where the header ends
        if not to_remove: # for when the method head     # TODO replace this regex with regex for '{' not parentheses (?)
            del caller_text[i]  #remove every line of the method header leading up to the end line
            i -= 1
        else:  # we are at the end line of the header
            caller_text[i] = caller_text[i].replace(to_remove.group(), '') # replace this line with empty string
            break
        i+=1
    # after this loop ^ we should have isolated just the caller method text for searching of interface
    if '::' in callee_method: #class defined
        tmp = ''
        done = True
        for line in caller_text:
            line = line.strip()
            if not done:  # if we haven't reached the end of the interface, i.e. it extends over many lines
                tmp = tmp + '\n' + line  #capture the lines
            if callee_method in line: #found start of interface
                done = False
                tmp = tmp + line  # capture it
            if ';' in line:   # if the line has a semicolon we know that we have reached the end
                done = True
            if done and tmp != '':  # we have the end of this interface, add it to the list and then reset tmp
                interface_text.append(tmp)
                tmp = ''
        if len(interface_text) == 0: #didn't find it with the class:: notation (usually because in method in same class)
            split = callee_method.split("::")  # here we will search for just the method name
            cclass = split[0].strip()
            cname = split[1].strip()
            for line in caller_text:
                line = line.strip()
                if not done:                 # same process as previous loop but doesn't include ClassName:: in search
                    tmp = tmp + '\n' + line  # this happens in C++ when the namespace is implicit
                if cname in line: #found start
                    done = False
                    tmp = tmp + line
                if ';' in line:
                    done = True
                if done and tmp != '':
                    interface_text.append(tmp)
                    tmp = ''
    else: #there is no class defined (ex. memset, or other built in functions, or C style methods with no class)
        tmp = ''
        done = True
        for line in caller_text:  # same method as above, searches method text and appends results to a list
            line = line.strip()
            if not done:
                tmp = tmp + '\n' + line
            if callee_method in line: #found start
                done = False
                tmp = tmp + line
            if ';' in line:
                done = True
            if done and tmp != '':
                interface_text.append(tmp)
                tmp = ''
    return interface_text # return list of lines where the caller interfaces the callee

def getReturnText(callee_sig):
    """
    Method to find the line where the callee has a return statement to the caller
    Again, this only uses a simple regex statement and so it may not produce the 'actual'
    return statement that the method will return to the callerself.
    In its current iteration, also only returns the FIRST return statement that the regex finds
    """
    if regexReturnTypes(callee_sig[0]) == 'void':  # checks first to see if the method in question even has a return type
        return 'void'
    else:
        nocomments = commentRemover(callee_sig[1])  # don't want to trip the regex on comments
        regex1 = re.compile(r'[1-9]{1,5}[ -~]*return .+?;', re.MULTILINE | re.DOTALL)  # compile regex to search the text for return statements
        ans = "\n".join(regex1.findall(nocomments))
        if len(ans) == 0 :
            return "Unable to locate return statement"  #if for some reason the code can't find the return, or doesn't know the method is void
        else:
            return ans
