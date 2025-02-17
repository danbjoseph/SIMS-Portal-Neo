from flask import request, render_template, url_for, flash, redirect, jsonify, Blueprint
from SIMS_Portal.models import Assignment, User, Emergency, Portfolio
from SIMS_Portal import db, login_manager
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, current_user, logout_user, login_required
from SIMS_Portal.assignments.forms import NewAssignmentForm
from datetime import datetime
from datetime import date, timedelta
import pandas as pd

assignments = Blueprint('assignments', __name__)

@assignments.route('/assignment/new', methods=['GET', 'POST'])
@login_required
def new_assignment():
	form = NewAssignmentForm()
	if form.validate_on_submit():
		assignment = Assignment(user_id=form.user_id.data.id, emergency_id=form.emergency_id.data.id, start_date=form.start_date.data, end_date=form.end_date.data, role=form.role.data, assignment_details=form.assignment_details.data, remote=form.remote.data)
		print(assignment)
		db.session.add(assignment)
		db.session.commit()
		flash('New assignment successfully created.', 'success')
		return redirect(url_for('main.dashboard'))
	return render_template('create_assignment.html', title='New Assignment', form=form)

@assignments.route('/assignment/new/<int:dis_id>', methods=['GET', 'POST'])
@login_required
def new_assignment_from_disaster(dis_id):
	form = NewAssignmentForm()
	emergency_info = db.session.query(Emergency).filter(Emergency.id == dis_id).first()
	if form.validate_on_submit():
		assignment = Assignment(user_id=form.user_id.data.id, emergency_id=dis_id, start_date=form.start_date.data, end_date=form.end_date.data, role=form.role.data, assignment_details=form.assignment_details.data, remote=form.remote.data)
		print(assignment)
		db.session.add(assignment)
		db.session.commit()
		flash('New assignment successfully created.', 'success')
		return redirect(url_for('main.dashboard'))
	return render_template('create_assignment_from_disaster.html', title='New Assignment', form=form, emergency_info=emergency_info)

@assignments.route('/assignment/<int:id>')
@login_required
def view_assignment(id):
	assignment_info = db.session.query(Assignment, User, Emergency).join(User).join(Emergency).filter(Assignment.id == id).first()
	dict_assignment = assignment_info.Assignment.__dict__
	dict_start_date = str(dict_assignment['start_date'])
	dict_end_date = str(dict_assignment['end_date'])
	
	formatted_start_date = datetime.strptime(dict_start_date, '%Y-%m-%d').strftime('%d %b %Y')
	formatted_end_date = datetime.strptime(dict_end_date, '%Y-%m-%d').strftime('%d %b %Y')
	
	days_left = db.engine.execute("SELECT JULIANDAY(:end_date) - JULIANDAY(DATE('now')) AS days_remaining FROM Assignment WHERE id = :id", {'id': id, 'end_date': dict_end_date})
	days_left_dict = days_left.mappings().first()
	days_left_int = int(days_left_dict['days_remaining'])
	print(f"days left value is: {days_left_int}")
	
	assingment_length = db.engine.execute("SELECT JULIANDAY(:end_date) - JULIANDAY(:start_date) AS length FROM Assignment WHERE id = :id", {'id': id, 'end_date': dict_end_date, 'start_date': dict_start_date})
	assignment_length_dict = assingment_length.mappings().first()
	assignment_length_int = int(assignment_length_dict['length'])
	print(f"assignment length value is: {assignment_length_int}")
	
	assingment_portfolio = db.session.query(Portfolio).filter(Portfolio.assignment_id==id, Portfolio.product_status=='Active').all()
	
	# get availability if reported and convert to list, else return empty list
	if assignment_info.Assignment.availability:
		assignment_availability = assignment_info.Assignment.availability
		remove_brackets = assignment_availability.replace('[','').replace(']','').replace("'",'')
		available_dates = remove_brackets.split(', ')

		# available_dates = []
		# for date in dates:
		# 	available_dates.append(datetime.strptime(date,'%Y-%m-%d').strftime('%b %d'))
		# print(available_dates)
	else:
		available_dates = []
		
	return render_template('assignment_view.html', assignment_info=assignment_info, formatted_start_date=formatted_start_date, formatted_end_date=formatted_end_date, days_left_int=days_left_int, assignment_length_int=assignment_length_int, assingment_portfolio=assingment_portfolio, available_dates=available_dates)

@assignments.route('/assignment/delete/<int:id>')
@login_required
def delete_assignment(id):
	if current_user.is_admin == 1 or current_user.id == id:
		try:
			db.session.query(Assignment).filter(Assignment.id==id).update({'assignment_status':'Removed'})
			db.session.commit()
			flash("Assignment deleted.", 'success')
		except:
			flash("Error deleting assignment. Check that the assignment ID exists.")
		return redirect(url_for('main.dashboard'))
	else:
		list_of_admins = db.session.query(User).filter(User.is_admin==1).all()
		return render_template('errors/403.html', list_of_admins=list_of_admins), 403
	
@assignments.route('/assignment/availability/<int:assignment_id>/<start>/<end>', methods=['GET', 'POST'])
@login_required
def assignment_availability(assignment_id, start, end):
	assignment_info = db.session.query(Assignment, User, Emergency).join(User).join(Emergency).filter(Assignment.id == assignment_id).first()
	
	dict_assignment = assignment_info.Assignment.__dict__
	dict_start_date = str(dict_assignment['start_date'])
	dict_end_date = str(dict_assignment['end_date'])
	
	formatted_start_date = datetime.strptime(dict_start_date, '%Y-%m-%d').strftime('%d %b %Y')
	formatted_end_date = datetime.strptime(dict_end_date, '%Y-%m-%d').strftime('%d %b %Y')
	
	days_left = db.engine.execute("SELECT JULIANDAY(:end_date) - JULIANDAY(DATE('now')) AS days_remaining FROM Assignment WHERE id = :id", {'id': assignment_id, 'end_date': dict_end_date})
	days_left_dict = days_left.mappings().first()
	days_left_int = int(days_left_dict['days_remaining'])
	print(f"days left value is: {days_left_int}")
	
	assingment_length = db.engine.execute("SELECT JULIANDAY(:end_date) - JULIANDAY(:start_date) AS length FROM Assignment WHERE id = :id", {'id': assignment_id, 'end_date': dict_end_date, 'start_date': dict_start_date})
	assignment_length_dict = assingment_length.mappings().first()
	assignment_length_int = int(assignment_length_dict['length'])
	print(f"assignment length value is: {assignment_length_int}")
	
	start_date = datetime.strptime(start, "%Y-%m-%d")
	end_date = datetime.strptime(end, "%Y-%m-%d")
	def daterange(start_date, end_date):
		for n in range(int((end_date - start_date).days)):
			yield start_date + timedelta(n)

	start_day_of_week = pd.Timestamp(start_date)
	
	date_list = []
	for single_date in daterange(start_date, end_date):
		date_list.append(single_date.strftime("%Y-%m-%d"))
		
	index_list = []
	index = len(date_list)
	for x in range(index):
		index_list.append(x)
	output = dict(list(enumerate(date_list, 1)))

	return render_template('/assignment_availability.html', date_list=date_list, assignment_id=assignment_id, assignment_info=assignment_info, days_left_int=days_left_int, assignment_length_int=assignment_length_int, formatted_start_date=formatted_start_date, formatted_end_date=formatted_end_date,)

@assignments.route('/assignment/availability/result', methods=['GET', 'POST'])
@login_required
def assignment_availability_result():
	response = request.form.getlist('available')
	response_formatted = "{}".format(response)
	assignment_id = request.form.get('assignment_id')
	print(type(assignment_id))
	db.session.query(Assignment).filter(Assignment.id==assignment_id).update({'availability': response_formatted})
	db.session.commit()
	return redirect(url_for('assignments.view_assignment', id=assignment_id))