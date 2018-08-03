## N2 Chart Generation
NASA IV&amp;V summer 2018 project, Orion code analysis tool.
Automatically producing N2 charts based upon interfaces between methods within code, currently supporting the use of the analysis tool `Understand`

The `generate_n2.py` script will create an N2 chart with the interfaces between methods within the scope of the provided method. Read more about N2 Charts [here](https://en.wikipedia.org/wiki/N2_chart). The basic structure of an interface is as follows: the caller function is higher up on the diagonal, the callee method is further down on the diagonal. The "interface text" (how the caller invokes the callee) is where the horizontal row of cells to the right of the caller intersects the vertical row of cells above the callee. The "return text", or what the callee returns back to the caller, is in the cell where the vertical cells below the caller intersects the horizontal cells to the left of the callee. This effectively forms a sort of rectangle shape where the top left and bottom right corners are the caller and callee respectively, and the top right and bottom left corners are the interface/return text. If this explanation does not make perfect sense, there is a .png grapgical representation called `N2 charts
example.png` in this directory.

Interface and return texts are the "best guess", refer to the method text below or even to the docs if necessary.

Global and public objects that are modified within each method are included in the grey side bars on the left side and running along the top. The cell directly above and to the left of the method cell contains any modified objects.

At the bottom of the sheet there are extra rows of helpful information, including the method text as well as lists of interfaces that method is a part of.

**Log any issues you encounter in the repo issues page at the top with detailed explanation, this is a work in progress.**

## Important notes
- If you want to keep versions of the interfaces.db file or the excel sheet and don't want them to be overwritten by the script the easiest way to preserve them is to rename them or move them from the same directory as the script so you don't accidentally lose data.
- If the script errors out during/after data insertion, the database file becomes corrupted and you have to use a fresh interfaces.db file on the next execution of the script. This is because the interface collection and the data insertion assumes that branches of methods have been traversed completely. At this current iteration of the script it does not support partial data insertion and then reusing the same database, it can become problematic for later analysis.
- If there are multiple versions of a template or constructor defined in the docs the script doesn't know automatically which version of the constructor the interface is invoking, and will prompt you to choose one.
- This script supports using a differently names .db file, but only use a .db file that was previously created by this script and renamed, otherwise the script will not work correctly

Below are directions for NASA employees to get started on using this tool (Updated 6/28/2018)
### Getting started
First, you must open your copy of `Understand` with the current iteration of FSW you are using.
In the upper toolbar ribbon click on the **Reports** tab and then click on **Generate Reports**
- Reports
  - Generate Reports
    - HTML Reports

The goal here is to get the html reports in a folder. Navigate through the menu and select an appropriate
location for the html report folder to be generated. Remember this folder path.


The next thing you must do is download this repo. The easiest way to do this is to select the
**Clone or Download** option above in a large green button and download the .zip of this repo.
The files that we will be needing for chart generation today are
```
generate_n2.py
regexMethodSignatures.py
regexMethodSignaturesPatterns.py
collect_globals.py
data_collection.py
createTables.py
```
Unzip and save these files to an appropriate folder.

Next you must get the correct tools installed to use this script.
You will need the following tools/packages for this to work.
- Python 3.4+
- Pip3 (Python package manager)
- BeautifulSoup
- Xlsxwriter

You can install Python first from the python website, and from 3.4+ python includes pip.

Next you must install the two critical packages: run in the command line
```
pip install xlsxwriter
pip install bs4
```
If you get an error that pip is unrecognized in your instance of command line then there is
no PATH variable registered for it. The default location for pip is: `<version>` will be replaced with your version, ex. 3.4 = Python34
```
C:\Python<version>\Scripts
```
Add this to your path and restart command line, or type
```
C:\Python<version>\Scripts\pip3.exe install xlsxwriter
C:\Python<version>\Scripts\pip3.exe install bs4
```
If you run into unforseen issues with python, pip, beautifulsoup or xlsxwriter, there are plenty of
documentation on the web.

Now run the .py script called generate_n2 and follow the onscreen directions to input
the **ClassName::MethodName** exactly as how it appears in the reports
as well as the html folder path for the reports that we generated earlier. Then follow the rest of the directions
about whether or not you want to use the interfaces.db file if it is already there.

This script supports displaying the global and public objects that each method uses/sets and the script will prompt whether you would like to use this feature. The sql file it produces `globals.db` only has to be compiled once every time the FSW version changes, after that simply select 'Y' when prompted to use the file in successive uses of the script.

**If the folder path or the ClassName::MethodName is wrong it will not work**

Be patient and let it run, if the function requested is not in the database and the script has to collect from reports then then it may take an extremely long time depending
how extensive the interface chain is. It will generate an excel file in the same
directory as the .py script called _n2_chart_ This is what you want. If you choose to use the existing `interfaces.db` file successive chart generation will get faster and faster as interfaces and methods continue to be saved.

**The globals.db file must be deleted and remade for every new project/FSW release. However, the globals.db file only needs to be created once per project.**
