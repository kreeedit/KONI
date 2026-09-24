<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="html" indent="yes"/>
  <xsl:param name="css">
    <xsl:text>

body {
    margin: 10;
    font-family: "Lucida Grande",Verdana,Helvetica,Arial,sans-serif;
}


	td { padding: 0.25em;
     margin: 0.25em }
     
   div#pos {
    display: block;
    text-align: left;
    margin: 5px 0;
    font-weight: bold;
    padding: 5px 3px;
    margin-left: 1%

}

div#senses {
	width:70%;
}

.info {
  display:block;
	float: right;
	clear:right;
	position:relative;
    top:-75px; left:0;
	padding: 15px 0 0 0;
	z-index:100;
	width:400px;
	color: #993300;
    text-align: center;
	filter: alpha(opacity:90);
	KHTMLOpacity: 0.90;
	MozOpacity: 0.90;
	opacity: 0.90;
}

.info2 {
  display:block;
	float: left;
	clear:right;
	position:relative;
    top:-50px; left:-150;
	padding: 15px 0 0 0;
	z-index:100;
	width:400px;
	color: #993300;
    text-align: center;
	filter: alpha(opacity:90);
	KHTMLOpacity: 0.90;
	MozOpacity: 0.90;
	opacity: 0.90;
}

.top{
	display: block;
	padding:3px 8px 10px;
    background: url(/img/bubble400.gif) no-repeat top;
}
.middle{ /* different middle bg for stretch */
	display: block;
	font:14px Arial,Helvetica,sans-serif; 
	padding: 0 8px; 

	background: url(/img/bubble_filler400.gif) repeat bottom; 
}
.bottom{
	display: block;
	padding: 40px 8px 0;
	color: #548912;
    background: url(/img/bubble400.gif) no-repeat bottom;
}


div#syntax {
    border: 2px double #bbb;
    padding: 2px;
    margin: 12px 0;
    margin-left: 5%
}

div#sentence {
    padding: 2px;
    margin: 50px 0;
}

div#sparse {
   background-color: #ccbbcc;
   width: 70%;
   border: 2px double #bbb;
    padding: 5px;
    margin: 50px 0;
}

div#collocate {
    margin-left: 10%
}


  </xsl:text>
  </xsl:param>

  <xsl:template match="/">
	<html>
	  <head>
		<title>Lexical Entry</title>
		   <style type="text/css">
			  <xsl:copy-of select="$css"/>
		  </style>
			<script type="text/javascript" src="/js/toggle.js"></script>
		</head>
		<body><xsl:apply-templates/></body>
	</html>
</xsl:template>

  
    <xsl:template match="lexicalEntry">


        	<table width="100%">
        	<tr>
        			<td>
						<xsl:apply-templates select="form"/>
        			</td>
        			
        <!-- div class="info2" id="freqbox" style="display: none"><span class="top"/><span class="middle">With a per10K frequency of <xsl:value-of select="per10K"/>, you will encounter <xsl:value-of select="form"/> on average once every <xsl:value-of select="round(10000 div per10K)"/> words.</span><span class="bottom"/></div -->

        			 <td align="right">       	   
        			 	<xsl:apply-templates select="per10K"/>
					</td>
				</tr>  
        
        		      		
        			
        			       
			</table>
			
			<xsl:apply-templates select="posContainer"/>

    	
    		<xsl:if test="count(/lexicalEntry/posContainer) = 0">	
         		<div id="sparse">
         		<xsl:text>Sorry!  We don't have enough data to figure out what this word means.</xsl:text>
         		</div>
         	</xsl:if>
         	
  </xsl:template>
  
      <xsl:template match="form">
   <font size="+3"><b> <xsl:apply-templates/></b></font>
  </xsl:template>


       <xsl:template match="gender">
        
    		<xsl:if test=". = 'm'">
        	(masc)
        	</xsl:if>
        	<xsl:if test=". = 'f'">
        	(fem)
        	</xsl:if>  
        	<xsl:if test=". = 'n'">
        	(neut)
        	</xsl:if>
        </xsl:template>
        
        <xsl:template match="date" />
        <xsl:template match="senseContainer/count" />
        <xsl:template match="lexicalEntry/count" />
        <xsl:template match="posContainer/count" />
        <xsl:template match="per10K">
    
    		<xsl:if test=". &gt;= 3">
        	[High Frequency]
        	</xsl:if>
        	<xsl:if test=". &gt;= .5 and . &lt; 3">
        	[Medium Frequency]
        	</xsl:if>  
        	<xsl:if test=". &lt; .5">
        	[Low Frequency]
        	</xsl:if>
        	<!-- xsl:value-of select="."/> per 10K words) -->
        </xsl:template>

        <xsl:template match="pos">
   <xsl:apply-templates/>
  </xsl:template>
  
      <xsl:template match="posContainer">
      <div id="pos">

      
          <xsl:apply-templates select="pos"/>
          <xsl:apply-templates select="gender"/>

          <xsl:apply-templates select="senses"/>
          <xsl:apply-templates select="syntaxContainer"/>
          <xsl:apply-templates select="sentences"/>

          	<xsl:if test="count(senses/senseContainer) = 0 and count(sentences) = 0">
         		
         		<div id="sparse">
         		<xsl:text>Sorry!  We don't have enough data to figure out what this word means.</xsl:text>
         		</div>
         	</xsl:if>
         	
         	
      </div>
  </xsl:template>

      <xsl:template match="senses">
      <div id="senses">
            <xsl:if test="count(senseContainer) != 0">

				<div class="info" id="sensebox" style="display: none"><span class="top"/><span class="middle"><xsl:value-of select="../../form"/> is translated as "<xsl:value-of select="senseContainer[1]/sense"/>" <xsl:apply-templates select="senseContainer[1]/prob"/> of the time in all Greek texts.
    		 		
    		
    		<xsl:if test="count(senseContainer/authorContainer) != 0">	
				Authors in parentheses use that sense more frequently than other authors.
				</xsl:if>
        		
		
		<xsl:for-each select="senseContainer[position() != 1 and count(authorContainer) > 0][1]">
			<xsl:value-of select="authorContainer/author[1]/name"/>, for example, commonly uses <xsl:value-of select="../../../form"/> to mean "<xsl:value-of select="sense"/>."
		</xsl:for-each>
		
		
				</span><span class="bottom"/>
				</div>
				</xsl:if>
				<ul>

      
          <xsl:for-each select="senseContainer">

 				<li> 	
 				<font color="blue">
					<a><xsl:attribute name="title"><xsl:value-of select="sense"/></xsl:attribute><xsl:attribute name="href">http://nlp.perseus.tufts.edu/hopper/dynlex.jsp?l=<xsl:value-of select="sense"/>&amp;r=0&amp;la=en</xsl:attribute><xsl:value-of select="sense"/></a></font>
				<xsl:text> (</xsl:text><xsl:apply-templates select="prob"/><xsl:text>)</xsl:text>
				<xsl:apply-templates select="authorContainer"/>
				
				<xsl:if test="position() = 1">			
										<xsl:text> [</xsl:text><a id="displayText" href="javascript:toggle3(['sensebox', 'syntaxbox', 'freqbox']);">Explain</a><xsl:text>]</xsl:text>
				</xsl:if>
				</li>
         </xsl:for-each>
               </ul>
               </div>

  </xsl:template>
 
       <xsl:template match="authorContainer">

         <xsl:text> (</xsl:text> 
         <xsl:for-each select="author">

					<em><xsl:value-of select="name"/></em>

		

				<xsl:if test="position()!=last()">
					<xsl:text>, </xsl:text>
				</xsl:if>
         </xsl:for-each>
         <xsl:text>)</xsl:text>
  </xsl:template>
  
  
     <xsl:template match="syntaxContainer">

      <div id="syntax">
        <div class="info" id="syntaxbox" style="display: none"><span class="top"/><span class="middle">Syntactic behavior learned from the Greek <a href="http://nlp.perseus.tufts.edu/syntax/treebank">treebank</a>, along with the authors who particularly illustrate it.</span><span class="bottom"/></div>
      <ul>
          <xsl:apply-templates/>
      </ul>
      </div>
  </xsl:template>
        <xsl:template match="collocation">
      <div id="collocate">
        <li>
        	<xsl:apply-templates select="original"/>
        	<xsl:apply-templates select="trans"/>
        	<!-- xsl:apply-templates select="loglikelihood" xsl:apply-templates select="count" -->
            <xsl:apply-templates select="authorContainer"/>

        
        </li>
      </div>
  </xsl:template>
 
        <xsl:template match="type">
          <xsl:apply-templates/><xsl:text>:</xsl:text>
  </xsl:template>
 
         <xsl:template match="sentences">
         	<xsl:if test="count(../senses/senseContainer) = 0">
         		
         		<div id="sparse">
         		<xsl:text>We don't have enough data to figure out what this word means, but here are some sentences it appears in.</xsl:text>
         		</div>
         	</xsl:if>
                <div id="sentence"><em><xsl:text>Example sentences.</xsl:text></em><p><ul>
            <xsl:for-each select="sentence">
				<li><xsl:apply-templates select="originalSentence"/> ("<xsl:value-of select="translation"/>"). <xsl:value-of select="citation"/>.</li>
       </xsl:for-each>
              	</ul></p>

 </div>                     					 

 </xsl:template>
  
      <xsl:template match="translation">
       
		<xsl:text> ("</xsl:text><xsl:apply-templates/><xsl:text>"). </xsl:text>
		
	  </xsl:template>
	  
        <xsl:template match="relativeFreq" />
        
        <xsl:template match="loglikelihood" >
		<xsl:apply-templates/>
        </xsl:template>
 
         <xsl:template match="prob" ><xsl:value-of select="round(. * 100)"/>%</xsl:template>
 
      <xsl:template match="trans">
       
       <xsl:if test=". != 'null'">
		<xsl:text> ("</xsl:text><xsl:apply-templates/><xsl:text>"). </xsl:text>
		</xsl:if>
       
       <xsl:if test=". = 'null'">
		<em><xsl:text> (N/A) </xsl:text></em>
		</xsl:if>
		</xsl:template>
	  
      <xsl:template match="senseContainer">
		<xsl:apply-templates select="sense"/>		
		<xsl:if test="not(position()=last())">, </xsl:if>

		
	  </xsl:template>	  
	  
      <xsl:template match="senseContainer/sense">
       <font color="blue">
		<xsl:value-of select="." />
		</font>
		
	  </xsl:template>
    <xsl:template match="focus">
		<font color="#7E3117"><xsl:apply-templates/></font>
	  </xsl:template>
	  
	  
      <xsl:template match="author">
		<xsl:text>(</xsl:text><xsl:apply-templates/><xsl:text>)</xsl:text>

	  </xsl:template>
</xsl:stylesheet>
