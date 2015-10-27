# This file contains the submission material for the Udacity Nanodegree
# Introduction to Programming by Jes H.
#
# Written for Python 2.7
#
# Google App Engine with Jinja2 applied to show the course notes.
# Commenting functionality per lesson and other stuff implemented.
#
# TODO:
# - get user from the post form input in lesson 4.3
#
# Link to Google App Engine live page:
# http://udacity-notes-on-gae.appspot.com

import re
import cgi
import urllib

# Required to ensure only utf-8 formatted characters are shown
import sys
reload(sys)
sys.setdefaultencoding('utf8')

# Required to enable parsing and manipulation of xml DOM
from xml.dom import minidom

# Jinja and Google App Engine libraries and environment variables
import os
import webapp2
import jinja2
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext import ndb

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(
	loader = jinja2.FileSystemLoader(template_dir),
	autoescape = True)

# -------------------- GOOGLE APP ENGINE WEBPAGE HANDLERS --------------------

# Google App Engine classes
class Handler(webapp2.RequestHandler):
	'''Generic Handler; will be inherited by more specific path Handlers'''
	def write(self,*a,**kw):
		"Write strings to the website"
		self.response.out.write(*a,**kw)

	def render_str(self,template,**params):
		"Render Jinja2 templates"
		t = jinja_env.get_template(template)
		return t.render(**params)

	def render(self,template,**kw):
		"Write Jinja2 template to the website"
		self.write(self.render_str(template,**kw))

class MainPage(Handler):
	def get(self):
		page_selector = self.request.get('page')
		self.render('root_welcome.html', page = page_selector)

class NotesHandler(Handler):
	'''Handler for showing the notes pages'''
	def get(self):
		page_selector = self.request.get('page')
		user_form_input = self.request.get('q','') # Used to hold user input in lesson 4.3
		stage1_list = make_lesson_list(load_stage('templates/notes_stage1_raw.html'))
		stage2_list = make_lesson_list(load_stage('templates/notes_stage2_raw.html'))
		stage3_list = make_lesson_list(load_stage('templates/notes_stage3_raw.html'))
		stage4_list = make_lesson_list(load_stage('templates/notes_stage4_raw.html'))
		stage5_list = make_lesson_list(load_stage('templates/notes_stage5_raw.html'))
		self.render('notes.html',
								page = page_selector,
								q = user_form_input,
								stage1 = stage1_list,
								stage2 = stage2_list,
								stage3 = stage3_list,
								stage4 = stage4_list,
								stage5 = stage5_list)

class FizzBuzzHandler(Handler):
	'''Handler for showing the Fizzbuzz page'''
	def get(self):
		page_selector = self.request.get('page')
		buzz_default = 0
		buzz_input = self.request.get('buzz', buzz_default)
		buzz_input = buzz_input and abs(int(buzz_input))
		self.render('fizzbuzz.html',
								page = page_selector,
								buzz = buzz_input)

class APIHandler(Handler):
	'''Handler for showing the CodePen.io API interaction page'''
	def get(self):
		page_selector = self.request.get('page')
		current_pens = codepen("http://codepen.io/popular/feed/")
		self.render('codepen.html',
		            page = page_selector,
		            codepens = current_pens)

# -------------- CODEPEN API FUNCTION TO PROCESS RSS FEED --------------

class penClass():
  '''basic placeholder class for extracted data from codepen rss feeds'''

def codepen(rss_url):
  '''Process Codepen.io rss feed and return list of objects with
  pen_title, pen_url, pen_hash, user_name, user_url, pen_creator properties'''
  # Read the RSS URL with urllib and parse the xml result through minidom
  # for easier manipulation and readability of the file structure
  result = urllib.urlopen(rss_url).read()
  dom_result = minidom.parseString(result)

  # Walk through the DOM structure and retrieve all elements tagged with "item"
  # These are the elements containing codepen details
  channels = dom_result.getElementsByTagName('channel')[0]
  items = channels.getElementsByTagName('item')
  codepens = [penClass() for i in range(len(items))]
  for index, pen in enumerate(codepens):
    pen.pen_title = items[index].getElementsByTagName('title')[0].firstChild.data
    pen.pen_url = items[index].getElementsByTagName('link')[0].firstChild.data
    url_split = pen.pen_url.split("/")
    pen.pen_hash = url_split[-1]
    pen.user_name = url_split[3]
    pen.user_url = 'http://codepen.io/' + pen.user_name
    pen.pen_creator = items[index].getElementsByTagName('dc:creator')[0].firstChild.data
  return codepens


# ----------------- VALIDATION HELPERS FOR USER INPUTS -----------------

def clean_html(raw_html):
	'''Strip text for html and return clean result'''
	cleanr = re.compile('<.*?>') # check for html tags with regular expression
	clean_text = re.sub(cleanr,'', raw_html)
	return clean_text

def check_profanity(text):
	'''Visit a webpage to check if text is profane. Return boolean True/False'''
	url = 'http://www.wdyl.com/profanity?q='
	query = urllib.quote(text) # Format the query appropriately for use in url
	output = urlfetch.fetch(url + query) # Get the webpage output
	result = output.content # Read the page result - this site returns a dict
	if "true" in result: # Therefore, look in that dict for true/false
		return True
	elif "false" in result:
		return False

# ---------- COMMENT/WALLPOST FUNCTIONALITY USING GAE DATASTORE ----------

# Wall post/comment classes with Google App Engine Datastore
# We set a parent key on the 'Post' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent.  However, the write rate should be limited to
# ~1/second.
def wall_key(wall_name):
	'''Constructs a Datastore key for a Wall entity.
	We use wall_name as the key'''
	return ndb.Key('Wall', wall_name)

def build_posts(posts):
	'''Take fetched database entries in posts and build an html wall'''
	# Create the posts html to print on the comments pages
	posts_html = ''
	# Build a post consisting of date, time, user name and comment with html allowed:
	for post in posts:
		# Newline character '\n' tells the computer to print a newline when the browser is
		# rendering the html.
		posts_html += '<div><h4>On ' + str(post.date.strftime('%d-%b-%Y %H:%M')) + ' ' + post.author.name + ' wrote:</h4>\n'
		posts_html += '<blockquote>' + cgi.escape(post.content) + '</blockquote>\n'
		posts_html += '</div>\n'
	return posts_html

def post_validation(user, comment):
	'''Validate user and comment input strings, return tuple (False/True, error string)'''
	error = ''
	# Check user name for html, add to error if html found, but allow to continue
	critical = False
	validated_author = clean_html(user)
	if validated_author != str(user):
		error += "Don't use html with user names. "
	# Check for empty/blank user name, add to error if true and do not allow to continue
	if validated_author.strip() == '':
		error += 'No user name found. '
		critical = True
	# Check for swear words. Totally not accepted!
	if check_profanity(comment) == True or check_profanity(validated_author) == True:
		error += 'No dang swear words allowed! '
		critical = True
	# Check for whitespace in user and comment
	if not comment.strip() or not validated_author.strip():
		error += 'Pure whitespace or blank fields not allowed. '
		critical = True
	return critical, error

# These are the objects that will represent our Author and our Post. We're using
# Object Oriented Programming to create objects in order to put them in Google's
# Datastore. These objects inherit Googles ndb.Model class.
class Author(ndb.Model):
	'''Sub model for representing an author'''
	# I'll just keep it simple and store a user name
	name = ndb.StringProperty(indexed=False)

class Post(ndb.Model):
	'''A main model for representing an individual post entry'''
	author = ndb.StructuredProperty(Author)
	content = ndb.StringProperty(indexed=False)
	date = ndb.DateTimeProperty(auto_now_add=True)

class WallPage(Handler):
	'''Shows the input form page for new posts and also renders all former posts below'''
	def get(self):
		page_selector = self.request.get('page','')
		wall_name = self.request.get('lesson')
		error = self.request.get('error')
		# [START query]
		posts_query = Post.query(ancestor = wall_key(wall_name)).order(-Post.date)
		# fetch() returns all posts that satisfy our query and returns a list of post objects
		posts = posts_query.fetch()
		# [END query]
		# Create the posts html to print on the comments pages
		posts_html = build_posts(posts)
		# These parameters are passed to the input form on the comments page so the form in turn
		# can include those parameters to the Post request. The lesson-wall gets carried over this way
		# from notes --> comments --> Post and is the ancestor key for each Datastore entity (=wall)
		sign_query_params = urllib.urlencode({'wall_lesson': wall_name})
		# Write out the comments page here
		self.render('commentbook.html',
								page = page_selector,
								lesson = wall_name,
								params = sign_query_params,
								posts = posts_html,
								error_message = error)

class PostWall(webapp2.RequestHandler):
	'''Adds a new post to the database'''
	def post(self):
		# Same parent key on the 'Post' to ensure each Post is in the same entity group.
		# Queries across the single entity group will be consistent.
		#
		# Pluck the lesson and username when directed here from the notes page
		# and prepare a post using the lesson name as Key
		wall_name = self.request.get('wall_lesson')
		post = Post(parent=wall_key(wall_name))
		# Get the content from our request parameters, in this case, the user name
		# is in the parameter 'user' and message in 'comment' from the submission form
		user_name = self.request.get('user')
		user_comment = self.request.get('comment')
		# Validate user input for critical errors, function returns a tuple
		critical_error, error = post_validation(user_name, user_comment)
		# If no critical errors, allow to continue with post to the database
		if critical_error == False:
			post.author = Author(name=clean_html(user_name))
			post.content = user_comment
			# Write to the Google Datastore
			post.put()
		# And finally a page redirect back to the comments page with same lesson set as the "wall"
		# This way the user can immediately see his/her new comment added to the top.
		# (It's the lesson-wall ancestor key circling back)
		self.redirect('/comment?lesson=' + wall_name + '&error=' + error)

# --------------- GOOGLE APP ENGINE PARAMETERS FOR WEBPAGE HANDLERS ---------------

# Part of the Google App Engine code together with MainPage class. Recognizes
# a certain path structure (e.g. '/') and uses the matching class for response.
app = webapp2.WSGIApplication([('/', MainPage),
															 ('/notes', NotesHandler),
															 ('/codepen', APIHandler),
															 ('/fizzbuzz', FizzBuzzHandler),
															 ('/comment', WallPage),
															 ('/sign', PostWall),
															], debug=True)

# -------- HELPER FUNCTIONS TO READ RAW STAGE NOTE TEMPLATE AND RETURN LIST --------

# Keys that _must_ be used in notes files to mark the content
LESSON_KEY, CONCEPT_KEY, CONCEPT_END = '// LESSON //', '// CONCEPT //', '// CONCEPT END //'

def load_stage(file_name):
	'''Loads lessons + concepts from a text/html course stage file'''
	with open(file_name,'r') as file_input:
		lines = file_input.readlines()
	# lines will be a list that contains all of our lines.
	# We use the String.join technique to join all of our elements in the list
	return ''.join(lines)

# To be optimized later for 1) less clunkiness, 2) validated input, 3) search by regular
# expressions, 4) storage by OOP (stage <-- lesson <-- concept objects)
def make_lesson_list(text):
	'''Takes text file containing all lessons with concepts text, returns a nested list containing Lesson, Concept Title and Concept Description, [['L1', ['C1', 'D']], ['L2', ['C2', 'D']],...]'''
	stage_list = [] # Container list for final output
	lesson_list = [] # Intermediate container list for lesson contents
	lesson_ready = True # Gatekeeper for closing/opening a fresh intermediate lesson container
	cr_len = 1 # The lenght of one linebreak (carriage return)
	while text != '': # Loop until the complete text of lessons+concepts is chipped down to nothing
		next_lesson_start = text.find(LESSON_KEY) + len(LESSON_KEY) + cr_len # Find start index of next lesson
		next_lesson_end = text.find(CONCEPT_KEY) # ...and end index
		next_concept_start = text.find(CONCEPT_KEY) + len(CONCEPT_KEY) + cr_len # Same procedure for concepts
		next_concept_end = text.find(CONCEPT_END)
		if (next_lesson_end >= 0 and lesson_ready == True): # If gate is open, it's time for new lesson
			lesson = text[next_lesson_start:next_lesson_end - cr_len] # Snip out the lesson headline
			lesson_list.append(lesson) # Store headline in intermediate lesson list
			text = text[next_lesson_end:] # Shorten text by lesson key + lesson headline
			lesson_ready = False # Close the gate for lesson collection
		elif next_concept_end >= 0: # If gate was closed, it's time to add concepts to the lesson list
			concept_str = text[next_concept_start:next_concept_end - cr_len] # Snip out the next concept
			next_cr = concept_str.find('\n') # Location of next linebreak (\n)
			concept_title = concept_str[:next_cr] # Concept title is first line (ends at linebreak)
			concept_body = concept_str[len(concept_title) + cr_len:] # Concept description is the rest
			concept_list = [concept_title, concept_body] # Wrap the concept in its own little list
			lesson_list.append(concept_list) # Add that concept list to the current lesson list
			text = text[next_concept_end + len(CONCEPT_END) + cr_len:] # Shorten text to cut away last concept
			if text.find(LESSON_KEY) == 0: # Look what's next in text. If new lesson is up, it's time to...
				stage_list.append(lesson_list) # Wrap latest intermediate lesson list in stage list
				lesson_list = [] # Clear the intermediate lesson list, so ready for next lesson
				lesson_ready = True # Tell gatekeeper a new lesson is coming up
			else: # If the next in text wasn't a new lesson, then keep finding concepts
				lesson_ready = False # To find concepts, gatekeeper must know we're not ready for a new lesson
	if stage_list != []: stage_list.append(lesson_list) # Put last lesson list into the stage list
	return stage_list # Time to return the nicely wrapped up lessons + concepts

