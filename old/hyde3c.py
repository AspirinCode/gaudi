###########################################################
# CHIMERA SCRIPT
# Rotate selected bonds, find clashes and H bonds
# By Jaime RG <jaime.rogue@gmail.com>, in UAB
###########################################################

## VERSION 3c
# nogui behaviour fixed
""" It's kind of hackish, since it STDOUT output
 	doesn't provide summary lines, but it works and
	it's faster than file parsing
"""

## KNOWN ISSUES
""" 1. If the session contains open dialogs, it will screw
#	nogui behaviour. Still don't know why :/
# 	2. If a bond rot already defined by a previous operation
#	is redefined with a new ID, it will complain and stop.
"""

## TODO
""" 1. Save and Restore original state
	2. Rebuild given coodinates from scratch
 	3. BUILD COORDINATES MAP
 		Maybe we don't want a fixed step?
"""

import os
import sys
from itertools import tee, islice, chain, izip, product
import argparse
import chimera
from chimera import runCommand as rc #cmd line features
from chimera import replyobj, UserError

def getBonds():
	## Parse current selection and write Midas-compatible selection string
	## using :id@first-atom@second-atom 
	results = []
	for bond in chimera.selection.currentBonds():
			results.append(":" + str(bond.atoms[0].residue.id) + "@" + str(bond.atoms[0].name) + "@" + str(bond.atoms[1].name))
	return results

def parComparison(some_iterable):
	## Returns the iterable in tuples of two, lazily
    prevs, items = tee(some_iterable, 2)
    prevs = chain([None], prevs)
    return izip(prevs, items)

def closeDialog(name):
	# Close requested dialog if open
	from chimera import dialogs
	for d in dialogs.activeDialogs():
		if d.name == name:
			d.Close()
			break
	#dialogs.find('name').Close()

def activateRotation(selected_bonds, reverse=False):
	## Activates selected bonds for rotation
	## TODO: Smart reverse option, based on picked anchor

	i = 0
	if (reverse): 
		reverse = 'reverse '
	else:
		reverse = ''
	for bond in selected_bonds:
		try:
			rc("rotation " + str(i) + " " + reverse + bond)
		except:# chimera.UserError:
			rc("~rotation " + str(i))
			rc("rotation " + str(i) + " " + reverse + bond)
		i += 1

def rotate(index, degrees):
	## Python wrapper for rotation Chimera command
	rc("rotation " + str(index) + " " + str(degrees))

def getReplyLog (chunk=100, flush=False):
	from chimera import dialogs, replyobj, UserError

	if "IDLE" in replyobj.currentReply().__doc__:
		raise UserError("Sorry, IDLE must be closed.")

	#dialogs.find('reply',create=1).enter()
	r = dialogs.find('reply').text.get('1.0','end')[-chunk:].split("\n")
	if flush:
		replyobj.currentReply().flush()
	return r


def performCalc():
	## Calculates H bonds and clashes for current position of current selection
	if chimera.nogui: #read from stdout
		# Capture STDOUT (somehow)
		from cStringIO import StringIO
		backup = sys.stdout
		sys.stdout = StringIO() #capture output
		#calculate hbonds & clashes
		rc("findhbond selRestrict any cacheDA true log true")
		hbonds_output = sys.stdout.getvalue()
		sys.stdout.close()
		sys.stdout = StringIO()
		rc("findclash ligand makePseudobonds false log true")
		clashes_output = sys.stdout.getvalue()
		sys.stdout.close()
		sys.stdout = backup # restore original stdout
		# Release STDOUT

		# Parse STDOUT
		clashes = clashes_output.splitlines()[7].split()[0]
		hbonds = 0
		for line in hbonds_output.splitlines():
			if line[:1] == ':' :
				hbonds += 1
	else: #read from reply log
		#calculate H bonds
		rc("findhbond selRestrict any cacheDA true log true")
		hbonds = getReplyLog(50,flush=True)[-3].split()[0]
		#calculate clashes
		rc("findclash ligand makePseudobonds false log true")
		clashes = getReplyLog(50,flush=True)[-3].split()[0]
	
	if clashes == "No" :
		clashes = 0
	
	# return hbonds, clashes
	return hbonds, clashes

def performCalcCore(hbonds=True, clashes=True):
	## Calculates H bonds and clashes for current position of current selection
	## Using native Chimera-Python interface
	results = []
	if (hbonds):
		pass
	if (clashes):
		pass

	return results	


def takeSnapshot(indices,wd):
	# takes a photo of current position
	rc("copy file " + wd + "img/" + "_".join(map(str,indices)) + ".jpg")

###########################
#/ END OF FUNCTIONS
############################

# ARGUMENT PARSING
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--degrees',
					required=False,
					type=int,
					default=90, 
					dest="step",
					metavar="<number of degrees>",
					help="Degrees for each rotation" )
parser.add_argument('-r', '--reverse',
					required=False, 
					default=False,
					dest="reverse",
					action='store_true',
					help="Wether to move heavy or light half" )
args = parser.parse_args()
#### /ARGUMENT PARSING


#working directory
wd = os.path.dirname(os.path.realpath(sys.argv[0])).replace('\\', '/') + '/'
rc("cd " + wd)

# Check bond is selected
if not chimera.selection.currentBonds():
	raise UserError("Please, select one or more bonds.")


# Activate rotation for selected bonds
selected_bonds = getBonds()
activateRotation(selected_bonds, args.reverse)
#closeDialog('build structure')

# Select ligand that contains bond
rc("sel :" + str(chimera.selection.currentBonds()[0].atoms[0].residue.id))
rc("namesel ligand") #save sel
# Focus
rc("focus ligand")

output = open(wd + "data.csv", 'w')
output.write("#Chosen bonds;--->;" + " & ".join(selected_bonds) + "\n")
output.write("Coordinates;Contacts;H bonds;\n")

## CORE
# Explore and evaluate

i = 0
for prev, curr in parComparison(product(xrange(0,360,args.step), repeat=len(selected_bonds))):

	print "----\nCoordinate " + str(curr)
	# Calculate starting position ALWAYS
	if (prev == None) :
		clashes, hbonds = performCalc()
		# if (int(clashes) == 0): 
		# 	takeSnapshot(curr, wd)
		output.write(str(curr) + ";" + str(clashes) + ";" + str(hbonds) + "\n")
		continue

	for a in xrange(0,len(prev)):
		if (prev[a] != curr[a]):
			# rotate
		 	rotate(a, curr[a] - prev[a])

 	# get score of current position
	clashes, hbonds = performCalc()
	# if (int(clashes) == 0): 
	#	takeSnapshot(curr, wd)
	output.write(str(curr) + ";" + str(clashes) + ";" + str(hbonds) + "\n")

	# progress
	i += 1
	total_rotations = (360/args.step)**len(selected_bonds)
	progress = 100*i/total_rotations
	if not progress % 5:
		print "Progress: " + str(progress) + "% done.\n"

output.close()

rc("~sel")
replyobj.status("OK. Check results in data.csv in script dir", blankAfter=5, log=True)