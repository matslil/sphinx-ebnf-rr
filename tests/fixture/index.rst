PlantUML Example
================

Hello World:

.. ebnf::
   :caption: A caption with **bold** text

   Hello ::= World

scale: 50%:

.. ebnf::
   :scale: 50 %

   Hello ::= World

width: 50%:

.. ebnf::
   :width: 50 %

   Hello ::= World

height: 400px:

.. ebnf::
   :height: 400px

   Hello ::= World

width: 10px * 1000%:

.. ebnf::
   :scale: 1000 %
   :width: 10px

   Hello ::= World

200x600px:

.. ebnf::
   :width:  200px
   :height: 600px

   Hello ::= World

Grammar:

.. ebnf::

   Grammar ::= Production*
   Production ::= NCName '::=' ( Choice | Link )
   NCName ::= [http://www.w3.org/TR/xml-names/#NT-NCName]
   Choice ::= SequenceOrDifference ( '|' SequenceOrDifference )*
   SequenceOrDifference ::= (Item ( '-' Item | Item* ))?
   Item ::= Primary ( '?' | '*' | '+' )*
   Primary ::= NCName | StringLiteral | CharCode | CharClass | '(' Choice ')'
   StringLiteral ::= '"' [^"]* '"' | "'" [^']* "'"	/* ws: explicit */ 
   CharCode ::= '#x' [0-9a-fA-F]+ /* ws: explicit */
   CharClass ::= '[' '^'? ( Char | CharCode | CharRange | CharCodeRange )+ ']' /* ws: explicit */
   Char ::= [http://www.w3.org/TR/xml#NT-Char]
   CharRange ::= Char '-' ( Char - ']' ) /* ws: explicit */ 
   CharCodeRange ::= CharCode '-' CharCode /* ws: explicit */ 
   Link ::= '[' URL ']'
   URL ::= S | Comment
   S ::= #x9 | #xA | #xD | #x20 '/*' ( [^*] | '*'+ [^*/] )* '*'* '*/' /* ws: explicit */ 

