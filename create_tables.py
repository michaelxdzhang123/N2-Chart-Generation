import sqlite3 as sql
import os
from collect_globals import collectGlobals


#-----------Table creation for interfaces.db-------------------#
# This file is pretty straightforward, just inline sql to create tables to hold the data
# classes table = collection of classes captured in data collection
# methods table = collection of methods found in data collection
# interfaces table = holds all information about interfaces between methods


def createTables(crsr):
    """Sequence of sql statements to create database"""
    # create interface table
    create_interfaces_table = """CREATE TABLE interfaces (
        interface_id INTEGER PRIMARY KEY AUTOINCREMENT,
        caller_dict_link VARCHAR(255),
        callee_dict_link VARCHAR(255),
        caller_signature VARCHAR(255),
        callee_signature VARCHAR(255),
        interface_text VARCHAR(500),
        return_text VARCHAR(100),
        caller_class VARCHAR(50) NOT NULL,
        callee_class VARCHAR(50) NOT NULL,
        caller_return_type VARCHAR(50) NOT NULL,
        callee_return_type VARCHAR(50) NOT NULL,
        caller_method_name VARCHAR(150) NOT NULL,
        callee_method_name VARCHAR(150) NOT NULL,
        caller_params VARCHAR(150) NOT NULL,
        callee_params VARCHAR(150) NOT NULL,
        FOREIGN KEY(caller_signature) REFERENCES methods(method_signature),
        FOREIGN KEY(callee_signature) REFERENCES methods(method_signature),
        FOREIGN KEY(caller_dict_link) REFERENCES methods(dict_link),
        FOREIGN KEY(callee_dict_link) REFERENCES methods(dict_link)
        );"""
    crsr.execute(create_interfaces_table)

    # create methods table
    create_methods_table = """CREATE TABLE methods (
        method_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dict_link VARCHAR(255), /*UNIQUE,  this is the link to this method in data dictionary */
        method_signature VARCHAR(255), /*, UNIQUE */
        class_name VARCHAR(50) NOT NULL,
        method_name VARCHAR(150) NOT NULL,
        return_type VARCHAR(50) NOT NULL,
        global_vars_modded VARCHAR(255),  /*insert these as a comma separated list*/
        params VARCHAR(150) NOT NULL,
        method_text VARCHAR(2000) NOT NULL,
        FOREIGN KEY(class_name) REFERENCES classes(class_name)
        );"""
    crsr.execute(create_methods_table)

    # create table of classes
    create_classes_table = """CREATE TABLE classes (
        class_name VARCHAR(50)
        );"""
    crsr.execute(create_classes_table)

    print("Tables created....")




def globalsTable(folder_path): #returns T/F if we are using globals
    """
    Initialization sequence to prompt user whether we are using globals table or not
    Takes user through series of Y/N prompts to make a new db and collect or not use one at all     
    """
    if not os.path.isfile("globals.db"): #no globals db
        print("\nNo table found of global variables. Would you like to collect global variables for this project? This WILL take a long time. (Y/N)")
        inp = input()
        inp = inp.strip()
        while( inp not in ['N', 'n', 'Y', 'y' ] ):
            print('Invalid input, try again')
            inp = input()
            inp = inp.strip()
        if inp == 'y' or inp == 'Y':
            collectGlobals(folder_path)  # calls to collectGlobals in collect_globals.py
            print('Global variables collected\n')
            return True
        elif inp == 'n' or inp == 'N':
            print("Generating N2 chart withot global variables...")
            return False
        else:
            print('Invalid input, exiting script')
            k = input()
            exit()
    else:
        print('Global variables database found, would you like to use existing database? (Y/N)')
        k = input()
        if k == 'y' or k == 'Y':
            print("Ok, using existing")
            return True
        elif k == 'n' or k == 'N':
            print("Ok, would you like to collect the globals for this project in a new database? (Y/N) \nWARNING: This will delete existing globals.db file")
            l = input()
            if l == 'y' or l == 'Y':
                print('Ok, making fresh globals.db')
                os.remove('globals.db')
                collectGlobals(folder_path) # calls to collectGlobals in collect_globals.py
                print('Globals.db created\n')
                return True
            elif l == 'n' or l == 'N':
                print('Ok, globals objects will not be included.')
                return False
            else:
                print("ERROR: Invalid input")
                exit()
        else:
            print("ERROR: Invalid input")
            exit()
