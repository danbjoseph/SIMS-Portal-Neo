from flask import request, render_template, url_for, flash, redirect, jsonify, Blueprint
from SIMS_Portal.models import Assignment, User, Emergency, Alert, user_skill, user_language, user_badge, Skill, Language, NationalSociety, Badge, Story
from SIMS_Portal import db
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
from SIMS_Portal.main.forms import MemberSearchForm, EmergencySearchForm, ProductSearchForm, BadgeAssignmentForm
from collections import defaultdict, Counter
from datetime import date, timedelta

main = Blueprint('main', __name__)

@main.route('/') 
def index(): 
	latest_stories = db.session.query(Story, Emergency).join(Emergency, Emergency.id == Story.emergency_id).order_by(Story.id.desc()).limit(3).all()
	return render_template('index.html', latest_stories=latest_stories)
	
@main.route('/about')
def about():
	return render_template('about.html')
	
@main.route('/admin_landing', methods=['GET', 'POST'])
@login_required
def admin_landing():
	badge_form = BadgeAssignmentForm()
	if request.method == 'GET' and current_user.is_admin == 1:
		pending_users = db.session.query(User, NationalSociety).join(NationalSociety, NationalSociety.ns_go_id==User.ns_id).filter(User.status=='Pending').all()
		all_users = db.session.query(User, NationalSociety).join(NationalSociety, NationalSociety.ns_go_id == User.ns_id).filter(User.status == 'Active').order_by(User.firstname).all()
		assigned_badges = db.engine.execute("SELECT u.id, u.firstname, u.lastname, GROUP_CONCAT(b.name, ', ') as badges FROM user u JOIN user_badge ub ON ub.user_id = u.id JOIN badge b ON b.id = ub.badge_id WHERE u.status = 'Active' GROUP BY u.id ORDER BY u.firstname")
		return render_template('admin_landing.html', pending_users=pending_users, all_users=all_users, badge_form=badge_form, assigned_badges=assigned_badges)
	elif request.method == 'POST': 
		user_id = badge_form.user_name.data.id
		badge_id = badge_form.badge_name.data.id
		# get list of assigned badges, create column that concats user_id and badge_id to create unique identifier
		badge_ids = db.engine.execute("SELECT user_id || badge_id as unique_code FROM user_badge")
		list_to_check = []
		for id in badge_ids:
			list_to_check.append(id[0])
		# check list against the values we're trying to save, and proceed if user doesn't already have that badge
		if (str(user_id) + str(badge_id)) not in list_to_check:
			return redirect(url_for('main.badge_assignment', user_id=user_id, badge_id=badge_id))
		else:
			flash('Cannot add badge - user already has it.', 'danger')
			return redirect(url_for('main.admin_landing'))
	else:
		list_of_admins = db.session.query(User).filter(User.is_admin==1).all()
		return render_template('errors/403.html', list_of_admins=list_of_admins), 403

@main.route('/badges')
def badges():
	badges = db.engine.execute("SELECT * FROM user_badge JOIN Badge ON Badge.id = user_badge.badge_id")
	count_active_members = db.session.query(User).filter(User.status == 'Active').count()

	count_list = []
	for badge in badges:
		count_list.append(badge[3])
	badge_counts = Counter(count_list)
	
	return render_template('badges.html', badge_counts=badge_counts, count_active_members=count_active_members)

@main.route('/badge_assignment/<int:user_id>/<int:badge_id>')
@login_required
def badge_assignment(user_id, badge_id):
	if current_user.is_admin == 1:
		new_badge = user_badge.insert().values(user_id=user_id, badge_id=badge_id)
		db.session.execute(new_badge)
		db.session.commit()	
		flash('Badge successfully assigned.', 'success')
		return redirect(url_for('main.admin_landing'))
	else:
		list_of_admins = db.session.query(User).filter(User.is_admin==1).all()
		return render_template('errors/403.html', list_of_admins=list_of_admins), 403

@main.route('/staging') 
@login_required
def staging(): 
	return render_template('visualization.html')

@main.route('/learning')
@login_required
def learning():
	return render_template('learning.html')

@main.route('/resources')
@login_required
def resources():
	return render_template('resources.html')

@main.route('/resources/colors')
@login_required
def resources_colors():
	return render_template('resources_colors.html')
	
@main.route('/resources/sims_portal')
@login_required
def resources_sims_portal():
	return render_template('sims_portal.html')

@main.route('/search/members', methods=['GET', 'POST'])
def search_members():
	member_form = MemberSearchForm()
	if request.method == 'GET':
		return render_template('search_members.html', member_form=member_form)
	if member_form.name.data or member_form.skills.data or member_form.languages.data: 
		name_search = member_form.name.data
		# convert name search to proper syntax for LIKE operator
		search_for_name = "'%{}%'".format(name_search)
		try:
			skill_search = member_form.skills.data.id
			skill_search_name = member_form.skills.data.name
		except:
			skill_search = 0
			skill_search_name = ''
		try:
			language_search = member_form.languages.data.id
			language_search_name = member_form.languages.data.name
		except:
			language_search = 0
			language_search_name = ''
		if name_search:
			name_query_converted = "SELECT user.id, firstname, lastname, email, job_title, slack_id FROM user WHERE firstname LIKE {} OR lastname LIKE {}".format(search_for_name, search_for_name)
			query_by_name = db.engine.execute(name_query_converted)
			result_by_name = [r._asdict() for r in query_by_name]
		else:
			query_by_name = db.engine.execute("SELECT user.id, firstname, lastname, email, job_title, slack_id FROM user WHERE firstname LIKE 'xxxx'")
			result_by_name = [r._asdict() for r in query_by_name]
	
		if skill_search:
			query_by_skill = db.engine.execute("SELECT user.id, firstname, lastname, email, job_title, slack_id FROM user JOIN user_skill ON user_skill.user_id = user.id JOIN skill ON skill.id = user_skill.skill_id WHERE skill_id = :skill", {'skill': skill_search})
			result_by_skill = [r._asdict() for r in query_by_skill]
		else:
			query_by_skill = db.engine.execute("SELECT user.id, firstname, lastname, email, job_title, slack_id FROM user JOIN user_skill ON user_skill.user_id = user.id JOIN skill ON skill.id = user_skill.skill_id WHERE skill_id = 0")
			result_by_skill = [r._asdict() for r in query_by_skill]
		if language_search:
			query_by_language = db.engine.execute("SELECT user.id, firstname, lastname, email, job_title, slack_id FROM user JOIN user_language ON user_language.user_id = user.id JOIN language ON language.id = user_language.language_id WHERE language_id = :language", {'language': language_search})
			result_by_language = [r._asdict() for r in query_by_language]
		else:
			query_by_language = db.engine.execute("SELECT user.id, firstname, lastname, email, job_title, slack_id FROM user JOIN user_language ON user_language.user_id = user.id JOIN language ON language.id = user_language.language_id WHERE language_id = 0")
			result_by_language = [r._asdict() for r in query_by_language]
		
		# merge all queries into one list
		master_search = {x['id']:x for x in result_by_language + result_by_skill + result_by_name}.values()
		return render_template('search_members_results.html', master_search=master_search)

@main.route('/search/emergencies', methods=['GET', 'POST'])
def search_emergencies():
	emergency_form = EmergencySearchForm()
	if request.method == 'GET':
		return render_template('search_emergencies.html', emergency_form=emergency_form)
	if emergency_form.name.data or emergency_form.status.data or emergency_form.type.data or emergency_form.location.data or emergency_form.glide.data: 
		emergency_search = emergency_form.name.data
		# convert name search to proper syntax for LIKE operator
		search_for_emergency = "'%{}%'".format(emergency_search)
		
		glide_search = emergency_form.glide.data
		# convert name search to proper syntax for LIKE operator
		search_for_glide = "'%{}%'".format(glide_search)
		try:
			status_search = emergency_form.status.data
		except:
			status_search = ''
		try:
			type_search = emergency_form.type.data.emergency_type_go_id
			type_search_name = emergency_form.type.data.emergency_type_name
		except:
			type_search = 0
			type_search_name = ''
		try:
			location_search = emergency_form.location.data.id
			location_search_name = emergency_form.location.data.country_name
		except:
			location_search = 0
			location_search_name = ''
			
		if emergency_search:
			emergency_query_converted = "SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE emergency_name LIKE {}".format(search_for_emergency)
			query_by_name = db.engine.execute(emergency_query_converted)
			result_by_name = [r._asdict() for r in query_by_name]
		else:
			query_by_name = db.engine.execute("SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE emergency_name LIKE 'xxxx'")
			result_by_name = [r._asdict() for r in query_by_name]

		if status_search:
			status_query_converted = "SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE emergency_status = '{}'".format(status_search)
			query_by_status = db.engine.execute(status_query_converted)
			result_by_status = [r._asdict() for r in query_by_status]
		else:
			query_by_status = db.engine.execute("SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE e.emergency_status LIKE 'xxxx'")
			result_by_status = [r._asdict() for r in query_by_status]

		if glide_search:
			glide_query_converted = "SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE e.emergency_glide LIKE {}".format(search_for_glide)
			query_by_glide = db.engine.execute(glide_query_converted)
			result_by_glide = [r._asdict() for r in query_by_glide]
		else:
			query_by_glide = db.engine.execute("SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE e.emergency_glide LIKE 'xxxx'")
			result_by_glide = [r._asdict() for r in query_by_glide]
			
		if type_search:
			type_query_converted = "SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE e.emergency_type_id = {}".format(type_search)
			query_by_type = db.engine.execute(type_query_converted)
			result_by_type = [r._asdict() for r in query_by_type]
		else:
			query_by_type =db.engine.execute("SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE e.emergency_type_id = 0")
			result_by_type = [r._asdict() for r in query_by_type]
			
		if location_search:
			location_query_converted = "SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE n.country_name = '{}'".format(location_search_name)
			query_by_location = db.engine.execute(location_query_converted)
			result_by_location = [r._asdict() for r in query_by_location]
		else:
			query_by_location =db.engine.execute("SELECT e.id, e.emergency_name, e.emergency_status, e.emergency_glide, n.country_name, t.emergency_type_name FROM emergency e JOIN nationalsociety n ON n.ns_go_id = e.emergency_location_id JOIN emergencytype t ON t.emergency_type_go_id = e.emergency_type_id WHERE n.country_name = 'xxxx'")
			result_by_location = [r._asdict() for r in query_by_location]
		
		# merge all queries into one list and remove duplicates
		master_search = {x['id']:x for x in result_by_name + result_by_glide + result_by_status + result_by_location + result_by_type}.values()
		
		return render_template('search_emergencies_results.html', master_search=master_search)

@main.route('/dashboard')
@login_required
def dashboard():
	todays_date = datetime.today()
	
	assignments_by_emergency = db.engine.execute("SELECT emergency_name, COUNT(*) as count_assignments FROM emergency JOIN assignment ON assignment.emergency_id = emergency.id WHERE assignment.assignment_status <> 'Removed' GROUP BY emergency_name")
	data_dict_assignments = [x._asdict() for x in assignments_by_emergency]
	labels_for_assignment = [row['emergency_name'] for row in data_dict_assignments]
	values_for_assignment = [row['count_assignments'] for row in data_dict_assignments]
	
	products_by_emergency = db.engine.execute("SELECT emergency_name , COUNT(*) as count_products FROM emergency JOIN portfolio ON portfolio.emergency_id = emergency.id WHERE portfolio.product_status <> 'Removed' GROUP BY emergency_name")
	data_dict_products = [y._asdict() for y in products_by_emergency]
	labels_for_product = [row['emergency_name'] for row in data_dict_products]
	values_for_product = [row['count_products'] for row in data_dict_products]
	
	count_active_assignments = db.session.query(Assignment, User, Emergency).join(User, User.id==Assignment.user_id).join(Emergency, Emergency.id==Assignment.emergency_id).filter(Assignment.assignment_status=='Active', Assignment.end_date>todays_date).count()
	active_assignments = db.session.query(Assignment, User, Emergency, NationalSociety).join(User, User.id==Assignment.user_id).join(Emergency, Emergency.id==Assignment.emergency_id).join(NationalSociety, NationalSociety.ns_go_id == User.ns_id).filter(Assignment.assignment_status=='Active', Assignment.end_date>todays_date).order_by(Emergency.emergency_name, Assignment.end_date).all()

	most_recent_emergencies = db.session.query(Emergency).order_by(Emergency.created_at.desc()).limit(7).all()
	most_recent_members = db.session.query(User, NationalSociety).join(NationalSociety, NationalSociety.ns_go_id == User.ns_id).filter(User.status == 'Active').order_by(User.created_at.desc()).limit(7).all()
	
	return render_template('dashboard.html', active_assignments=active_assignments, count_active_assignments=count_active_assignments, most_recent_emergencies=most_recent_emergencies, labels_for_assignment=labels_for_assignment, values_for_assignment=values_for_assignment, labels_for_product=labels_for_product, values_for_product=values_for_product, most_recent_members=most_recent_members)
	
	