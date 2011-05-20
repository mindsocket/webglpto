#!/usr/bin/python
from __future__ import print_function

gpl = r"""
    parse_pto.py - scan a pto file
    Copyright (C) 2010  Kay F. Jahnke

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# This module implements scanning of pto files. The scan is merely syntactic,
# meaning that (hopefully) all the various abbreviation letters are processed,
# but their meaning is ignored. Whether this approach is sufficient, remains
# to be seen - the advantage is relative ease of the scanning process.
# In the original pto documentation there are quite clear guidelines on
# what lines are what. If the line starts with a character from a defined
# character set, it is a meaningful line, everything else is ignored.
# By default, may parser is more liberal: If the line starts with any
# alphabetic character, it is considered meaningful. This allows for the
# parser to still work if new line types are added. As long as the data
# in the lines aren't structured differently than those in other lines,
# the scan will still succeed.
# A complication is added by various extensions to the original syntax.
# These usually come in the guise of comment lines - they start with a '#'
# character, and will be ignored by 'orhodox' pto syntax. But of course, they
# are meaningful. So I've made an effort to cater for what I call the
# 'ugly ducklings' and process them in a way that makes them accessible
# in an obvious way.
# I have also allowed for individual entries in lines to have
# any letter as prefix. There are some entry types which are preceded
# by multi-letter field qualifiers. This is regrettable, because it spoils
# the syntax which is, otherwise, quite clean. I have tried to accomodate
# all multi-character field type qualifiers - I can't be sure I know
# them all. If new multi-letter fields are introduced, the regular expressions
# of the scanner will have to be amended - this is luckily a trivial task.
# New single-letter field qualifiers will be accepted straight away.
# I've also made an effort to provide ample comments throughout the script.
# Things are explained in the order thay are implemented, it may be instructive
# to once read through the lot ;-)

import string
import sys
import re
import argparse

# the following set of characters are what I reckon is the standard set
# of accepted pto line headers. If you want to make the parser behave like in the
# original pto file specification, you can instead use the class strict_pto_scan,
# which does not allow arbitrary line headers. By default, all characters
# will be accepted as line headers.

standard_headers = 'pvimozck' # standard headers of pto line. Extend if needed.

# type dictionary for pto line members. these one-letter type qualifiers
# are what I use in the scan, they aren't part of pto file syntax

pto_data_type = dict ( { 'f' : 'float' ,
                            'i' : 'int' ,
                            'r' : 'rectangle' ,
                            'b' : 'back reference' ,
                            's' : 'string' ,
                            'w' : 'word' } )
        
# some 'ugly ducklings' here - undocumented extensions to the pto format.
# They have specific line beginnings which are recognized by these regular
# expressions:

hugin_extension_re = re.compile ( "\#\-hugin" )

hugin_option_re = re.compile ( "\#hugin_\S+" )

imgfile_extension_re = re.compile ( "\#\-imgfile" )

# I designed the regular expression for pto line members (data fields) below
# as best as I could figure it out from the scanty documentation; if there
# should be any errors they can easily be rectified by editing the sub-RE for
# the group member_qualifier, right in the beginning of the pto member RE.
# So this RE refers to members of 'proper' pto lines, like p-, c-, i-, etc. lines,
# and the assumption is that any newly introduced lines will use similar mechanisms
# to notate their data, i.e. by preceding the data field by a one-letter qualifier.

pto_member_re = re.compile ( r"""

    \s*                              # eat leading space

    # each member starts with a one-to-three letter abbreviation:
    
    (?P<member_qualifier> R[a-e]         # Ra, Rb, Rc, Rd, Re
                        | V[a-dxym]      # Va, Vb, Vc, Vd, Vx, Vy, Vm
                        | T[xyzrs][XYZ]* # too many to list ;-)
                        | E[rb]          # Er, Eb
                        | Eev            # EeV
                        | [A-Za-z] )     # plus all single letters. I'm liberal ;-)

    # that's followed by the member's value [no space in between]:

    (?P<member_text>
        (?P<float_value>           # might have a single float value
            [+-]?                  # optional sign, allow '+'
            (
               ( \d+ [.] \d* )     # either some digits . optionally some digits
               | ( [.] \d+ )       # or . some digits
            )
        )                          # float value done
        | (?P<rectangle_value>     # or an rectangle in lrtb notation
           (?P<left>[+-]?\d+),
           (?P<right>[+-]?\d+),
           (?P<top>[+-]?\d+),
           (?P<bottom>[+-]?\d+)
        )                          # rectangle value done
        | (?P<integral_value>      # or an integer
           [+-]?\d+
        )                          # integral value done
        | (?P<backref_value>       # or a back reference (has leading '=')
           =\d+
        )                          # back reference value done
        | (?P<string_value>        # or a string (for now, double quotes only)
           " ( [^"] | ( \\ " ) )* "
        )                          # string value done
        | (?P<word_value>          # 'word' value - just a sequence of non-space
           \S+
        )                          # word value done
    )                              # end of <member_text>
    """ , re.VERBOSE )

# now for the data types for the result of the scan of the pto lines:

# topmost is class pto_scan. This performs and contains the scan of a whole
# pto file. The scan is kept in a member variable 'sequential', which retains the
# same order as the input lines, but instead of mere text, each line is represented
# by a pto_line object which, in case of content-bearing lines, has information
# about the content of the line:
# the actual text found in the pto file, and a breakdown of it's content into a
# structured format so that individual data fields become easily accessible.
# The pto_scan object is created by passing it a pto file name.
# In a pto_scan object, you'll find these members:
#
# filename              - name of the pto file that was processed
# accepted_line_headers - set of characters that were accepted as line headers
# sequential            - list of internal representations of the file's
#                         lines; these are objects of type pto_line, see below
#
# further, optionally, if 'make_member_access()' was used:
#
# a member for every type of line that occured. These members
# are accessed by the appropriate letter, so if we have a pto_scan
# object by the name of s, access is by s.i (images), s.c (control points)
# etc., and will yield a list of pto_line objects of that type, so simplified
# access syntax along the lines of s.i[7] (the seventh i-line) is possible

class pto_scan :

    def __init__ ( self ,
                   pto_data ,
                   accepted_line_headers = string.letters ,
                   scan_extensions = True ,
                   member_access = True ) : # KFJ 2010-01-03 now per default

        # new KFJ 2010-12-27: allow open files as input
        if type ( pto_data ) == str :
            ptofile = open ( pto_data , 'r' )     # open the file
            self.filename = pto_data              # good to know
        elif hasattr ( pto_data , 'readlines' ) : # can it do readlines
            ptofile = pto_data                    # it's a duck
            self.filename = ptofile.name          # good to know
        else :
            print ( pto_data )
            raise NameError ( "no pto data found" )
        
        ptolines = ptofile.readlines()    # get the file's content
        ptofile.close()                   # we're done with the file

        self.accepted_line_headers = accepted_line_headers # we store that, too
        self.scan_extensions = scan_extensions # and that
        self.sequential = []              # that's where our scan goes

        lineiter = iter ( ptolines )      # make separate iter, so we can keep
                                          # iterating after the loop terminates
        lineno = -1                       # first increment will set it to start at 0

        for line in lineiter :            # as long as there are lines
            lineno += 1
            # accepted_line_headers contains all letters that will be accepted
            # as heading a valid pto line. Per default this will be any letter,
            # but it can be limited to just the 'canonical' line headers by
            # passing the appropriate string to __init__.

            if line[0] in accepted_line_headers :
                ptoline = pto_line ( line , lineno , line[0] , scan = True )

            elif line[0] == '#' : # this is a comment, but might be an extension

                if self.scan_extensions : # we look into the line to see if it's an extension

                    # the parade of the ugly ducklings...

                    if hugin_extension_re.match ( line ) :
                        # it's a hugin extension
                        ptoline = hugin_extension_line ( line , lineno , '#-hugin' )

                    elif hugin_option_re.match ( line ) :
                        # it's a hugin option
                        ptoline = hugin_option_line ( line , lineno )

                    elif imgfile_extension_re.match ( line ) :
                        # it's an 'imgfile extension line'
                        ptoline = imgfile_extension_line ( line , lineno , '#-imgfile' )

                    else:
                        # just a plain old comment
                        ptoline = pto_line ( line , lineno, '#' , scan = False )

                else : # scan_extensions is False
                    
                    # take this line as a comment
                    ptoline = pto_line ( line , lineno, '#' , scan = False )

            elif line[0] == '*' : # a line starting with a star means: ignore the rest
                ptoline = pto_line ( line , lineno , '*' , scan = False )
                self.sequential.append ( ptoline ) # since we break, we need to do this
                break

            else: # this shouldn't be a pto line, don't parse, but record. proceed.
                ptoline = pto_line ( line , lineno , '' , scan = False )

            self.sequential.append ( ptoline ) # append to sequential, loop

        # everything past the star we ignore, but we also record it
        for line in lineiter : # any trailing lines?
            lineno += 1
            ptoline = pto_line ( line , lineno , '' , scan = False )
            self.sequential.append ( ptoline )

        if member_access is True :    # this is the default now
            self.make_member_access()
            
    # make_member_access adds attributes to pto_scan and pto_line objects, so that
    # their content can be accessed by attribute notation. So, for example, to access
    # the third i-line's n field from a scan we made, we can write
    # scan.i[3].n
    # For other than standard pto lines (like the ugly ducklings), this is currently
    # not provided. Calling make_member_access is the default; it provides a handy
    # way of getting to the data, but if you just need a few specific fields, you may
    # not want to call it, particularly if your script is quite large.

    def make_member_access ( self ) :

        if hasattr ( self , '_member_access' ) : # this code is only executed once
            return                               # if called again, just ignore it
        else :
            self._member_access = True           # okay, first time called

        for line in self.sequential :

            # do we have a list of lines of this type already?

            if not hasattr ( self , line.header ) :

                # if not, we start one, and make it accessible as attribute
                # of the scan, accessible by the line header character
                setattr ( self , line.header , [] )
                
            # now we add all the members as attributes of the pto_line object,
            # accessible by their character combination. Note that the attribute's
            # value will not be the member's value but the whole member object.
            # This may seem awkward - when just looking at the data, an additional
            # indirection is needed, like
            # scn.i[3].n.value
            # for the third image's name, but it allows easy modification of the
            # member data as well:
            # scan.i[3].n.value = 'image_number_three.tif'

            if line.members :
                for m in line.members:
                    setattr ( line , m.type , m )
                getattr ( self , line.header ) . append ( line )

    # to get a subset of lines with a specific header, the scan can be asked to filter
    # for them. This is a mere hint in the direction; the filtering could be much more
    # sophisticated...
    
    def get_lines_like ( self , header_filter ) :

        return [ l for l in self.sequential if l.header == header_filter ]
    
    # the pto() routine will recreate a pto file from the data held
    # in the scan. The idea is, of course, that you have modified the data
    # in some form, and the generated pto will reflect these changes.
    # I've made an attempt to keep all comments and such, and to output
    # them in original order, but if you have seriously messed with the data,
    # things may not work out as wished. Caveat utilitor ;-)
    # if you do not care for comments and such to be included in the output,
    # call pto() with with_aux=False. Then it will only output lines that
    # have been considered meaningful in the scan.

    def pto ( self , target = sys.stdout , with_aux = True ) :
        for line in self.sequential :
            line.pto ( target , with_aux )

    # output of the parsed pto lines, grouped by type. You won't usually need this
    # routine, it's more of a test tool to see if the scan did what was anticipated.
    
    def walk ( self ) :

        print ( "scan of pto file %s" % self.filename )
        print ( "accepted line headers: %s" % self.accepted_line_headers )
        if self.scan_extensions :
           print ( "extensions were accepted" )
        print ( "total of %d lines" % len ( self.sequential ) )
        
        for line in self.sequential :
            line.walk()

    # just print all lines in order - yet another test procedure. It merely echoes
    # the input.
    
    def echo ( self ) :
        for line in self.sequential :
            print ( line.sourcecode , end = '' )

# this class, derived from pto_scan, will not scan arbitrary line headers.
# This implements the 'orthodox' behaviour where lines with unknown headers
# are simply ignored. The liberal approach to individual data fields is the
# same as in the base class, though.

class strict_pto_scan ( pto_scan ) :

    def __init__ ( self , filename , accept_extensions = True ) :
        pto_scan.__init__ ( self , filename , standard_headers , sccept_extensions ) 

# the pto_line object encapsulates the scan of a single pto line. It contains
# members that contain it's fields and also has the 'source code' line that
# it was created from and it's own 'header', which is the type letter in case
# of standard pto lines, and something appropriate for other lines.
# The scan is ignorant of semantics. This may have undesired side effects:
# If fields require float values, but the data in the file can be interpreted
# as integral, the associated type will be 'i'. Also, if a string is meant but
# the data can be interpreted as numeric, the numeric interpretation will
# be chosen. In all cases, the original character sequence of the token is
# recorded, though, in the pto_member object's member 'text'.
# When accessing member data, it may be advisable to type-check or explicitly
# convert them to the desired type before processing them. It's the back side
# of being liberal.
# Whether this approach poses any problems in real life remains to be seen,
# it was chosen for simplicity's and flexibility's sake.
# Note that there are several object types which inherit from pto_line. These
# contain scans of lines of various 'extension' types, but they are handled
# as if they were pto lines proper by being a bit lenient on what a pto line
# can contain in the first place. They can be identified by querying the
# type of the pto line object - or by looking at the 'header' data.
#
# in a pto_line object, these members will be present:
#
# sourcecode - the text, as found in the original pto file
# lineno     - the line number. empty lines are counted.
# header     - usually the pto line code, like p, i, o, c, etc.
#              if the line isn't a 'proper' pto line, header
#              will still contain an appropriate string.
#
# if the line is identified as carrying information, it will also
# have an additional member:
#
# members    - list of data fields in the line. These are of type
#              pto_member, see below

class pto_line :

    def __init__ ( self , line , lineno , header , scan = True ) :

        self.sourcecode = line      # bit of bookkeeping
        self.lineno = lineno        # in case meaningful messages are needed
        self.header = header        # mostly just a letter, but mind the ugly ducklings

        if not scan :               # scan==False means it's a comment or such
            self.members = None     # at any rate, it wasn't recoginzed as pto line
            return

        self.members = []           # okay, scan it for 'members'

        # okay, here we go. Throw the line into our magic regular expression
        # to get the data out.
        
        members = pto_member_re.finditer ( line , len ( header ) )

        for m in members :    # all constructs matching our re for members
            pm = pto_member() # will produce a pto_member object
            pm.type = m.group ( 'member_qualifier' ) # this is p,i,o,c etc.
                                                     # (see pto_data_type above)
            pm.separator = ''                        # may be set to '=', see below
            pm.text = m.group ( 'member_text' )      # we record the original text
            self.members.append ( pm )               # append pto_member to the list

            # now we extract the actual value from the match object
            fv = m.group ( 'float_value' )
            if fv :
                pm.value = float ( fv )
                pm.datatype = 'f'
                continue
            rv = m.group ( 'rectangle_value' )
            if rv :
                l = m.group ( 'left' )
                r = m.group ( 'right' )
                t = m.group ( 'top' )
                b = m.group ( 'bottom' )
                pm.value = ( int(l) , int(r) , int(t) , int(b) )
                pm.datatype = 'r'
                continue
            iv = m.group ( 'integral_value' )
            if iv :
                pm.value = int ( iv )
                pm.datatype = 'i'
                continue
            iv = m.group ( 'backref_value' ) # like, in i-lines, a=0 b=0 etc.
            if iv :
                pm.value = int ( iv[1:] )
                pm.datatype = 'b'
                pm.separator = '='  # only other place where separator is set
                continue
            sv = m.group ( 'string_value' )
            if sv :
                pm.value = sv[1:-1] # we unquote the string
                pm.datatype = 's'
                continue
            wv = m.group ( 'word_value' )
            if wv :
                pm.value = wv
                pm.datatype = 'w'
                continue
                
            # if we get to here, something went wrong
            raise SyntaxError ( "line %d:\n%s\nsomething went awfully wrong..." %
                                ( self.lineno , self.sourcecode ) )

    # find a specific member of the pto line. This is what you use if the data
    # in the scan haven't been made accessible as members by calling make_member_access().
    # Let's assume you need a control point's first image's x coordinate, then you'd
    # call select like
    # the_x_member = my_c_line.select ( 'x' )
    # and access it's value like
    # the_x_coordinate = x_member.value
    
    def select ( self , member_tag ) :
        for m in self.members:
            if m.type == member_tag :
                return m
        return None

    # extract will pick a specific member of a pto line by calling select and then
    # return the member's value, rather than the pto_member object.
    
    def extract ( self , member_tag ) :
        m = self.select ( member_tag )
        if m:
            return m.value
        return None

    # a pto_line contains it's header (in case of the base class the leading letter)
    # and a list of members. We make a string from that by basically recreating a
    # pto line from it.

    def __str__ ( self ) :
        s = self.header
        if self.members :
            for m in self.members :
                s += ' ' + str ( m )
        return s

    # pto() will (hopefully) create valid pto code from the pto_line object.
    # if with_aux is passed as False, comments and such will be suppressed.

    def pto ( self , target , with_aux = True ) :
        if self.members :
            target.write ( str ( self ) + '\n' )
        elif with_aux :
            target.write ( self.sourcecode )

    # just to check if things went okay, see comment with pto_scan's walk()

    def walk ( self ) :
        print ( "line %04d header '%s' source:" % ( self.lineno , self.header ) )
        print ( self.sourcecode  )
        if self.members :
            print ( "line contains %d member fields" % len ( self.members ) )
            for m in self.members :
                print ( '  ' , end = '' )
                m.walk()
        print()

# I wish I could have avoided the next section, but here it comes:
# A bunch of special cases dealing with 'extensions' people have
# thought out to make my life more difficult :-(

# Some 'non-critical' values are stored by hugin as key-value pairs in comment
# lines; I presume they refer to the line following them. I have set up the re
# for such lines so that it will recognize the obvious, but I can't be sure
# there isn't more evil trickery done...
# this is the re to scan elements in this line type:

hugin_key_value_re = re.compile ( r"""

    \s*                              # eat leading space

    # each member starts with key= tag, grab the key:
    
    (?P<member_qualifier> [^=\s]+)

    # next the '=' sign

    =
    
    # that's followed by the member's value [no space in between]:

    (?P<member_text>
        (?P<float_value>           # might have a single float value
            [+-]?
            (
               ( \d+ [.] \d* )
               | ( [.] \d+ )
            )
        )                          # float value done
        | (?P<integral_value>      # or an integer
           [+-]?\d+
        )                          # integral value done
        | (?P<string_value>        # or a string (for now, double quotes only)
           " ( [^"] | ( \\ " ) )* "
        )                          # string value done
        | (?P<word_value>          # 'word' value - just a sequence of non-space
           \S+
        )                          # word value done
    )                              # end of <member_text>
    """ , re.VERBOSE )

# and this is the class derived from pto_line to contain the scan of such a line.
# It is less complex than a pto line - for example, rectangles aren't recognized.
# Since I couldn't find documentation on the precise syntax of this line type,
# I'm reduced to guesswork.

class hugin_extension_line ( pto_line ) :

    def __init__ ( self , line , lineno , header ) :

        pto_line.__init__ ( self , line , lineno , header , scan = False )
        self.members = []

        members = hugin_key_value_re.finditer ( line , len ( header ) )
        for m in members :
            pm = pto_member()
            pm.type = m.group ( 'member_qualifier' )
            pm.separator = '='
            pm.text = m.group ( 'member_text' )
            self.members.append ( pm )
            fv = m.group ( 'float_value' )
            if fv :
                pm.value = float ( fv )
                pm.datatype = 'f'
                continue
            iv = m.group ( 'integral_value' )
            if iv :
                pm.value = int ( iv )
                pm.datatype = 'i'
                continue
            sv = m.group ( 'string_value' )
            if sv :
                pm.value = sv[1:-1] # we unquote the string
                pm.datatype = 's'
                continue
            wv = m.group ( 'word_value' )
            if wv :
                pm.value = wv
                pm.datatype = 'w'
                continue
                
            # if we get to here, something went wrong
            raise SyntaxError ( "line %d:\n%s\nsomething went awfully wrong..." %
                                ( self.lineno , self.sourcecode ) )
        
# next special case is what I've called a hugin option line. These are lines,
# typically at the end of the script, that contain various hugin settings, like
# which blender to use etc.
# I treat them as pto lines with the first word yielding the 'header' and everything
# following that the 'value' - often there is nothing following, so then the value is
# just an empty string. Since this structure is trivial, there is no specific re to
# scan it. Note that the members list will not be None if there is nothing following
# the header, but an empty list instead. This is to distinguish hugin option lines
# from 'meningless' lines.

class hugin_option_line ( pto_line ) :

    def __init__ ( self , line , lineno ) :

        m = hugin_option_re.match ( line )
        header = m.group ( 0 )
        pto_line.__init__ ( self , line , lineno , header , scan = False )
        self.members = []

        line = line.strip()
        if header < line : # some value after the header
            pm = pto_member()
            pm.type = ''
            pm.separator = ''
            pm.text = line [ len ( header ) + 1 : ]
            pm.datatype = 'w'
            pm.value = pm.text
            self.members.append ( pm )

# now some CPGs produce files with yet another complication.
# They put image data in o-lines and precedes these o-lines with
# more data in a line starting with '#-imgfile'. this line contains, as far as
# I can tell, the image's width, height, and name, untagged. Having thusly output
# these data, they are promptly omitted from the o-line.
# I found Panomatic and A. Jenny's autopano to do this.
# Here is the code to scan these lines:

imgfile_data_re = re.compile ( r"""

    \s*                            # eat leading space

    # as far as I can tell, the members are just plain single values without tags:

    (?P<member_text>
        (?P<float_value>           # might have a single float value
            [+-]?
            (
               ( \d+ [.] \d* )
               | ( [.] \d+ )
            )
        )                          # float value done
        | (?P<integral_value>      # or an integer
           [+-]?\d+
        )                          # integral value done
        | (?P<string_value>        # or a string (for now, double quotes only)
           " ( [^"] | ( \\ " ) )* "
        )                          # string value done
        | (?P<word_value>          # 'word' value - just a sequence of non-space
           \S+
        )                          # word value done
    )                              # end of <member_text>
    """ , re.VERBOSE )

# now this type of line needs yet another scanning mechanism. Here it comes:

class imgfile_extension_line ( pto_line ) :

    def __init__ ( self , line , lineno , header ) :

        pto_line.__init__ ( self , line , lineno , header , scan = False )
        self.members = []

        members = imgfile_data_re.finditer ( line , len ( header ) )
        for m in members :
            pm = pto_member()
            pm.type = '' # these buggers aren't type tagged
            pm.separator = ''
            pm.text = m.group ( 'member_text' )
            self.members.append ( pm )
            # I allow the following set of types, maybe more than necessary:
            fv = m.group ( 'float_value' )
            if fv :
                pm.value = float ( fv )
                pm.datatype = 'f'
                continue
            iv = m.group ( 'integral_value' )
            if iv :
                pm.value = int ( iv )
                pm.datatype = 'i'
                continue
            sv = m.group ( 'string_value' )
            if sv :
                pm.value = sv[1:-1] # we unquote the string
                pm.datatype = 's'
                continue
            wv = m.group ( 'word_value' )
            if wv :
                pm.value = wv
                pm.datatype = 'w'
                continue
                
            # if we get to here, something went wrong
            raise SyntaxError ( "line %d:\n%s\nsomething went awfully wrong..." %
                                ( self.lineno , self.sourcecode ) )

# class pto_member contains the information from individual data
# fields in pto lines. For example, if it's an i-line, it would
# contain a member like n"img1.tif". In the pto_member object,
# the folowing members will be found:
#
# type      - the leading string, like n, or EeV
# datatype  - a letter for the data type (see pto_data_type above)
# value     - it's content (of appropriate type, not just the string),
# text      - the original text (as a string).
# separator - usually '', but set to '=' in case of back references.
#             these are entries of the form a=0, meaning, 'use the a
#             value found in image number 0'.
#
# pto_member's construction is handled by the pto_line object,
#this is why there are only the __str__-type methods here.
    
class pto_member :

    # stringize. This should create valid pto code
    
    def __str__ ( self ) :
        if self.datatype == 's' :
            return '%s%s"%s"' % ( self.type , self.separator , self.value )
        elif self.datatype == 'r' :
            return '%s%s%d,%d,%d,%d' % ( self.type ,
                                         self.separator ,
                                         self.value[0] ,
                                         self.value[1] ,
                                         self.value[2] ,
                                         self.value[3] )
        return '%s%s%s' % ( self.type , self.separator , str ( self.value ) )

    # more verbose output displaying the structure of the scan
    
    def walk ( self ) :

        if self.datatype == 's' :
            content = '"%s"' % self.value
        elif self.datatype == 'b' :
            content = '=%d' % self.value
        elif self.datatype == 'r' :
            content = '(%d,%d,%d,%d)' % ( self.value[0] ,
                                          self.value[1] ,
                                          self.value[2] ,
                                          self.value[3] )
        else :
            content = '%s' % str ( self.value )
            
        print ( "field: '%s' data type: '%s' content: '%s'" %
                 ( self.type ,
                   pto_data_type [ self.datatype ] ,
                   content ) )

# If this module is used as a stand-alone program, it needs a main
# routine. For now this is mainly for testing. If parse_pto is imported,
# main() will not be called.
    
def main() :
    
    # we create an argument parser
    
    parser = argparse.ArgumentParser (
        formatter_class=argparse.RawDescriptionHelpFormatter ,
        description = gpl + '''
    this module contains a scanner for pto files.
    The development stage is alpha, testing has been
    sporadic so far and there is no functionality
    apart from merely performing the scan and running
    some analytical code. Documentation is in the
    comments in the file.

    If called with the -v option, the internal representation
    of the scan will be printed out, otherwise the internal
    representation will be reconverted into pto syntax and printed.

    ''' )
    
    parser.add_argument('-p', '--pto',
                        metavar='<pto file>',
                        type=str,
                        help='pto file to be processed')

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='produce verbose output')

    args = parser.parse_args( sys.argv[1:] )

    if len ( sys.argv ) < 2 :
        parser.print_help()
        return

    scan = pto_scan ( args.pto )
    scan.make_member_access()

    if args.verbose :
        scan.walk()
    else :
        scan.pto()

# Usually, this script will be imported by another script. In the rare case
# that it's called as a stand-alone script, it'll just scan the input file
# and play with it a bit. Take it as a unit test.

# are we main? if so, do the main thing...

if __name__ == "__main__":
    main()

# and that's it.
