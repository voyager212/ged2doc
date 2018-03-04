"""Module which produces LaTeX output.
"""

from __future__ import absolute_import, division, print_function

__all__ = ["LatexWriter"]

import logging
import pkg_resources
import string
import os

from shutil import copyfile
from ged4py import model
from .plotter import Plotter
from .size import Size
from . import utils
from . import writer


_log = logging.getLogger(__name__)

# this is no-op function, only used to mark translatable strings,
# to extract all strings run "pygettext -k TR ..."


def TR(x): return x  # NOQA


class LatexWriter(writer.Writer):
    """Transforms GEDCOM file into nicely formatted LaTeX page.

    This is a sub-class of :py:class:`~ged2doc.writer.Writer` class providing
    implementation for rendering methods which transform GEDCOM info into
    LaTeX constructs. Constructor takes a large number of arguments which
    configure appearance of the resulting LaTeX page. After instantiating
    an object of this type one has to call
    :py:meth:`~ged2doc.writer.Writer.save` method to produce output file.

    :param flocator: Instance of :py:class:`ged2doc.input.FileLocator`
    :param str output: Name for the output file or file object
    :param tr: Instance of :py:class:`ged2doc.i18n.I18N` class
    :param str encoding: GEDCOM file encoding, if ``None`` then encoding is
        determined from file itself
    :param str encoding_errors: Controls error handling behavior during string
        decoding, one of "strict" (default), "ignore", or "replace".
    :param sort_order: Determines ordering of person in output file, one of
        the constants defined in :py:mod:`ged4py.model` module.
    :param int name_fmt: Bit mask with flags from :py:mod:`ged2doc.name`
    :param bool make_images: If ``True`` (default) then generate images for
        persons.
    :param bool make_stat: If ``True`` (default) then generate statistics
        section.
    :param bool make_toc: If ``True`` (default) then generate Table of
        Contents.
    :param Size image_width: Size of the images.
    :param Size image_height: Size of the images.
    :param bool image_upscale: If True then smaller images will be
        re-scaled to extend to image size.
    :param int tree_width: Number of generations in ancestor tree.
    """


    def __init__(self, flocator, output, tr, encoding=None,
                 encoding_errors="strict",
                 sort_order=model.ORDER_SURNAME_GIVEN, name_fmt=0,
                 make_images=True, make_stat=True, make_toc=True,
                 paper_format="a4paper",
                 paper_orientation="portrait",
                 margin_left="0.5in", margin_right="0.5in",
                 margin_top="1.0in", margin_bottom="0.25in",
                 image_width="2in", image_height="2in",
                 tree_scale="1.0", descending_generations="2"):

        writer.Writer.__init__(self, flocator, tr, encoding=encoding,
                               encoding_errors=encoding_errors,
                               sort_order=sort_order, name_fmt=name_fmt,
                               make_images=make_images, make_stat=make_stat,
                               make_toc=make_toc)


        self._sexName = {}
        self._sexName['M'] = 'male'
        self._sexName['F'] = 'female'

        self._languageName = {}
        self._languageName['en'] = 'english'
        self._languageName['pl'] = 'polish'
        self._languageName['ru'] = 'russian'

        self._supportedFormats = ['a0paper', 'a1paper', 'a2paper', 'a3paper',
                                  'a4paper', 'a5paper', 'a6paper',
                                  'b0paper', 'b1paper', 'b2paper', 'b3paper',
                                  'b4paper', 'b5paper', 'b6paper',
                                  'c0paper', 'c1paper', 'c2paper', 'c3paper',
                                  'c4paper', 'c5paper', 'c6paper',
                                  'b0j', 'b1j', 'b2j', 'b3j', 'b4j', 'b5j', 'b6j',
                                  'ansiapaper', 'ansibpaper', 'ansicpaper',
                                  'ansidpaper', 'ansiepaper', 'letterpaper',
                                  'executivepaper', 'legalpaper']
        self._supportedOrientations = ['portrait', 'landscape']

        self._output = output
        self._margin_left = margin_left
        self._margin_right = margin_right
        self._margin_top = margin_top
        self._margin_bottom = margin_bottom
        self._paper_format = paper_format
        if not self._paper_format in self._supportedFormats:
          self._paper_format = 'a4paper'
        self._paper_orientation = paper_orientation
        if not self._paper_orientation in self._supportedOrientations:
          self._paper_orientation = 'portrait'

        self._tree_scale = float(tree_scale)
        if self._tree_scale > 2.0:
          self._tree_scale = 2.0
        if self._tree_scale < 0.01:
          self._tree_scale = 0.01

        self._descending_generations = int(descending_generations)

        if hasattr(output, 'write'):
            self._output = output
            self._close = False
        else:
            self._output = open(output, 'wb')
            self._close = True

    def _render_prolog(self):
        """Generate initial document header/title.
        """
        doc = ['\\documentclass[11pt, %s, twoside, %s]{report}\n' % (self._paper_format, self._paper_orientation)]
        doc += ['\\usepackage[utf8]{inputenc}\n']
        doc += ['\\usepackage[T2A,T1]{fontenc}\n']
        doc += ['\\usepackage[polish,russian,english]{babel}\n']
        doc += ['\\usepackage[all]{genealogytree}\n']
        doc += ['\\usepackage{incgraph}\n']
        doc += ['\\usepackage{graphicx}\n']
        doc += ['\\usepackage{wrapfig}\n']
        doc += ['\\usepackage{floatrow}\n']
        doc += ['\\usepackage{fancyhdr}\n']
        doc += ['\\usepackage{xcolor}\n']
        doc += ['\\usepackage{titlesec}\n']
        doc += ['\\usepackage{multicol}\n']
        doc += ['\\usepackage{calc}\n']
        doc += ['\\usepackage{enumitem}\n']
        doc += ['\\usepackage[export]{adjustbox}\n']
        doc += ['\\usetikzlibrary{backgrounds}\n\n']
        doc += ['\\usepackage[%s,bindingoffset=0.8in,' % self._paper_format]
        doc += ['left=%s,' % self._margin_left]
        doc += ['right=%s,' % self._margin_right]
        doc += ['top=%s,' % self._margin_top]
        doc += ['bottom=%s,' % self._margin_bottom]
        doc += ['headheight=20pt, footskip=.25in]{geometry}\n']

        doc += ['\\graphicspath{ {ged2doc.media/} }\n']

        doc += ['\\newcommand{\\sectionbreak}{\\clearpage}\n']

        doc += ['\\fancypagestyle{plain}{%\n']
        doc += ['\\fancyfoot[LE,RO]{\\thepage}\n']
        doc += ['\\cfoot{}\n']
        doc += ['}\n']

        doc += ['\\pagestyle{fancy}\n']
        doc += ['\\fancyfoot[LE,RO]{\\thepage}\n']
        doc += ['\\cfoot{}\n']
 
        doc += ['\\title{' + self._encTR("Ancestor tree") + '}\n']
        doc += ['\\author{Dariusz Kania}\n']
        doc += ['\\date{\\today}\n\n']
        doc += ['\\begin{document}\n\n']

        doc += ['\\selectlanguage{%s}\n' % self._languageName[self._tr._lang]]
        doc += ['\\setlist[description]{font=\\normalfont\\space, itemsep=0pt}']
        doc += ['\\maketitle\n\n']
        doc += ['\\newpage\\mbox{}\n']
        doc += ['\\thispagestyle{empty}\n\n']
        doc += ['\\clearpage\n']
        doc += ['\\setcounter{secnumdepth}{2}\n']
        doc += ['\\setcounter{tocdepth}{2}\n']
        doc += ['\\setcounter{page}{1}\n']
        doc += ['\\raggedbottom\n']

        if self._make_toc:
          doc += ['\\tableofcontents\n\n']

        for line in doc:
            self._output.write(line.encode('utf-8'))

    def _encTR(self, text):
      return self._enc(self._tr.tr(TR(text)))

    def _enc(self, text):
#      if self._tr._lang == 'ru':
#        return '\\foreignlanguage{russian}{%s}' % text
      return text

    def _interpolate(self, text):
        """Takes text with embedded references and returns proporly
        escaped text with HTML links.
        """
        result = ''
        for piece in utils.split_refs(text):
          if isinstance(piece, tuple):
            xref, name = piece
            result += name
          else:
            result += piece
        return self._enc(result)

    def _render_section(self, level, ref_id, title, newpage=False):
        """Produces new section in the output document.

        This method should also save section reference so that TOC can be
        later produced when :py:meth:`_render_toc` method is called.

        :param int level: Section level (1, 2, 3, etc.).
        :param str ref_id: Unique section identifier.
        :param str title: Printable section name.
        """
        if not title:
          return

        sectionType = {}
        sectionType[1] = 'chapter'
        sectionType[2] = 'section'
        sectionType[3] = 'subsection'

        doc = []
        doc += ['\\' + sectionType[level] + '{' + self._enc(title) + '}\n']
        doc += ['\\label{%s}\n' % ref_id]
        if level == 1:
          doc += ['\\thispagestyle{empty}\n']
          doc += ['\\newpage\n\n']

        for line in doc:
            self._output.write(line.encode('utf-8'))

    def _render_person(self, person, image_data, attributes, families,
                       events, notes):
        """Output person information.

        TExtual information in parameters to this method can include
        references to other persons (e.g. moter/father). Such references are
        embedded into text in encoded format determined by
        :py:meth:`_person_ref` method. It is responsibility of the subclasses
        to extract these references from text and re-encode them using proper
        bacenf representation.

        :param person: :py:class:`ged4py.Individual` instance
        :param bytes image_data: Either `None` or binary image data (typically
                content of JPEG image)
        :param list attributes: List of (attr_name, text) tuples, may be empty.
        :param list families: List of strings (possibly empty), each string
                contains description of one family and should be typically
                rendered as a separate paragraph.
        :param list events: List of (date, text) tuples, may be empty. Date
                is properly formatted string and does not need any other
                formatting.
        :param list notes: List of strings, each string should be rendered
                as separate paragraph.
        """

        doc = []

        if not person.name.first and not person.name.maiden and not person.name.surname:
          return
 
        if image_data:
          img = self._getImageFragment(person)
          if img:
            doc += [img]

        # all attributes follow
        if attributes:
          longestAttribute = ''
          for attr, value in attributes:
            if len(longestAttribute) < len(self._encTR(attr)):
              longestAttribute = self._encTR(attr)
          doc += ['\\makebox{}\n']
          doc += ['\\begin{description}[leftmargin=\\widthof{%s:mm},style=nextline]' % longestAttribute]
          for attr, value in attributes:
            doc += [ '\\item[%s:] %s\n' % (self._encTR(attr), self._interpolate(value)) ] 
          doc += ['\\end{description}\n']

        if families:
          doc += ['\\subsubsection{' + self._encTR("Spouses and children") + '}\n']
          doc += ['\\noindent\n']
          for family in families:
            doc += [ '%s\\\\\n' % self._interpolate(family) ] 

        if events:
          longestDate = ''
          for date, facts in events:
            if len(longestDate) < len(date):
              longestDate = date

          doc += ['\\subsubsection{' + self._encTR("Events and dates") + '}\n']
          doc += ['\\begin{description}[leftmargin=\\widthof{%s:mm},style=nextline]' % longestDate]
          for date, facts in events:
            doc += [ '\\item[%s:] %s\n' % (date, self._interpolate(facts)) ] 
          doc += ['\\end{description}\n']

        if notes:
          doc += ['\\subsubsection{' + self._encTR("Comments") + '}\n']
          for note in notes:
            doc += [ self._interpolate(note) + '\n']

        tree_svg = self._make_family_tree(person)
        if tree_svg:
          doc += ['\\subsubsection{' + self._encTR("Ancestor tree") + '}\n']
          doc += [tree_svg]
        else:
          doc += ['\\vskip{2ex}\n']

        for line in doc:
          self._output.write(line.encode('utf-8'))

    def _render_name_stat(self, n_total, n_females, n_males):
        """Produces summary table.

        Sum of male and female counters can be lower than total count due to
        individuals with unknown/unspecified gender.

        :param int n_total: Total number of individuals.
        :param int n_females: Number of female individuals.
        :param int n_males: Number of male individuals.
        """
        s = [self._encTR(t) for t in ['Person count', 'Female count', 'Male count'] ]
        longestDescription = ''
        for t in s:
          if len(t) > len(longestDescription):
            longestDescription = t

        doc = []
        doc = ['\\newlength{\\longestdesc}\n']
        doc += ['\\setlength{\\longestdesc}{\\widthof{%s }}\n' % longestDescription]
        doc += ['\\noindent\n']
        doc += ['\\makebox[\\longestdesc][l]{%s} %d\\\\\n' % (s[0], n_total)]
        doc += ['\\makebox[\\longestdesc][l]{%s} %d\\\\\n' % (s[1], n_females)]
        doc += ['\\makebox[\\longestdesc][l]{%s} %d\\\\\n' % (s[2], n_males)]
        doc += ['\\let\\longestdesc\\relax\n']

        for line in doc:
            self._output.write(line.encode('utf-8'))

    def _render_name_freq(self, freq_table):
        """Produces name statistics table.

        :param freq_table: list of (name, count) tuples.
        """
        def _gencouples(namefreq):
            halflen = (len(namefreq) + 1) // 2
            for i in range(halflen):
                n1, c1 = namefreq[2 * i]
                n2, c2 = None, None
                if 2 * i + 1 < len(namefreq):
                    n2, c2 = namefreq[2 * i + 1]
                yield n1, c1, n2, c2

        total = float(sum(count for _, count in freq_table))
        longestName = 'Aleksandra'

        tbl = ['\\newlength{\\longestname}\n']
        tbl += ['\\setlength{\\longestname}{\\widthof{%s }}\n' % longestName]
        tbl += ['\\begin{multicols}{3}\n']
        tbl += ['\\noindent\n']
        for name1, count1, name2, count2 in _gencouples(freq_table):
          tbl += ['\\makebox[\\longestname][l]{%s} %d, %.2f\\%%\\\\\n' % (name1 or '(-)', count1, 100.0*count1/total)]
          if count2 is not None:
            tbl += ['\\makebox[\\longestname][l]{%s} %d, %.2f\\%%\\\\\n' % (name2 or '(-)', count2, 100.0*count2/total)]
        tbl += ['\\end{multicols}\n']
        tbl += ['\\let\\longestname\\relax\n']

        for line in tbl:
          self._output.write(line.encode('utf-8'))

    def _render_toc(self):
        """Table of contents is produced automatically by LaTeX - no need to implement it.
        """

    def _finalize(self):
        """Finalize output.
        """
        doc = ['\\end{document}']
        for line in doc:
          self._output.write(line.encode('utf-8'))

        if self._close:
            self._output.close()

    def _getImageFragment(self, person):
        '''Returns LaTeX fragment placing person's image.
        '''
        doc = ''
        if not os.path.exists(utils.personImageFile(person)):
          return doc

        if not os.path.exists('ged2doc.media'):
          os.mkdir('ged2doc.media')

        fileName,extension = os.path.splitext(utils.personImageFile(person))
        newFileName = person.xref_id[1:-1] + extension
        copyfile(utils.personImageFile(person), 'ged2doc.media/' + newFileName)

        print( 'Copied file %s to ged2doc.media/%s' % (utils.personImageFile(person), newFileName))
        doc += '\\begin{wraptable}{r}{4.5cm}\n'
        doc += '\\includegraphics[width=\\textwidth,right]{%s}\n' % newFileName
        doc += '\\end{wraptable}\n'
        doc += '\\makebox{}\n'

        return doc

    def _make_family_tree(self, person):
        """"Returns genealogytree structure for parent tree or None.

        :param person: Individual record
        :return: Image data (XML contents), bytes
        """
        tree = ''
        if not person:
          return tree

        tree += '\\vskip 3ex\n'
        tree += '\\begin{centering}\n'
        tree += '\\begin{tikzpicture}[scale=%f,transform shape]\n' % self._tree_scale
        tree += '\\genealogytree[template=signpost,\n'
        tree += '                timeflow=down,\n'
        tree += '                options for node={probant}{box={colback=yellow!50}}]{\n'
        tree += self._makeTree(person) 
        tree += '}\n'
        tree += '\\end{tikzpicture}\n\n'
        tree += '\\end{centering}\n'
        return tree

    def _makeTree(self, person):
      tree = ''
      if not person:
        return;

      tree += self._addPersonAndSiblings(person, 0)

      indent = self._indent(-1)
      if person.mother:
        tree += indent + 'parent{\n  ' + self._node('g', person.mother, -1) + indent + '}\n'
      if person.father:
        tree += indent + 'parent{\n  ' + self._node('g', person.father, -1) + indent + '}\n'

      if len(tree) > 0:
        tree = '  sandclock{\n' + tree + '  }\n'

      return tree

    def _addPersonAndSiblings(self, person, gen):
      tree = ''
      if not person:
        return tree

      siblings = self._commonChildren(person.father, person.mother)
      for p in siblings:
        if p.xref_id == person.xref_id:
          tree += self._addSpouses(p, gen, 'probant')
        else:
          tree += self._addSpouses(p, gen)

      if len(tree) == 0:
        tree += self._addSpouses(person, gen, 'probant')

      return tree

    def _addSpouses(self, person, gen, probant=None):
      tree = ''
      if gen > self._descending_generations:
        return tree

      indent = self._indent(gen)
      if gen == self._descending_generations:
        tree = self._node('g', person, gen, probant)
      else:
        fams = person.sub_tags('FAMS')
        spouseNumber=0
        for fam in fams:
          spouse = writer._spouse(person, fam)
          if not spouse:
            continue
          spouseNumber += 1
          if spouseNumber == 1:
            tree += self._node('p', spouse, gen)
            tree += self._node('g', person, gen, probant)
            tree += self._addCommonChildren(person, spouse, gen+1)
          else:
            tree += indent + 'union{\n'
            tree += self._node('p', spouse, gen)
            tree += self._addCommonChildren(person, spouse, gen+1)
            tree += indent + '}\n'
        if len(tree) == 0:
          tree = self._node('g', person, gen, probant)

      tree = indent + 'child{\n' + tree + indent + '}\n'
      return tree

    def _addCommonChildren(self, person1, person2, gen):
      tree = ''
      if not person1 or not person2:
        return tree

      commonChildren = self._commonChildren(person1, person2)
      for child in commonChildren:
        if gen == self._descending_generations:
          tree += self._node('c', child, gen)
        else:
          tree += self._addSpouses(child, gen)

      return tree

    def _commonChildren(self, person1, person2):
      children = []
      if not person1 or not person2:
        return children

      childrenOfPerson1 = self._children(person1)
      childrenOfPerson2 = self._children(person2)
      for c1 in childrenOfPerson1:
        for c2 in childrenOfPerson2:
          if c1.xref_id == c2.xref_id:
            children.append(c1)

      return children

    def _children(self, person):
      children = []
      if not person:
        return []
      fams = person.sub_tags('FAMS')
      for fam in fams:
        children += fam.sub_tags('CHIL')
      return children

    def _indent(self, gen):
      if gen < 0:
        return '    ' + '  ' * (abs(gen)-1)
      return '    ' + '  ' * gen

    def _node(self, nodeType, person, gen, nodeId=None):
      if not person:
        return ''
      indent = self._indent(gen+1)
      sex = self._sexName[person.sex]
#      page = '(\\pageref{%s})' % person.xref_id[1:-1]
      if nodeId:
        return indent + '%s[%s, id=%s]{%s %s}\n' % (nodeType, sex, nodeId, person.name.first, person.name.surname)
      else:
        return indent + '%s[%s]{%s %s}\n' % (nodeType, sex, person.name.first, person.name.surname)

    def _birthdate(self, person):
      birthday = person.sub_tag('BIRT/DATE')
      if not birthday:
        return ''
      return '\\\\\\gtrsymBorn\\,%s' % self._tr.tr_date(birthday.value)

