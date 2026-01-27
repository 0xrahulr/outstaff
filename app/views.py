from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Organization, OrganizationMember, Note, Expense, LeaveRequest, ActivityLog
import csv
import requests


def log_activity(organization, user, action):
    """Helper function to log activities"""
    ActivityLog.objects.create(
        organization=organization,
        user=user,
        action=action
    )


@login_required
def organization_detail(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    context = {
        'organization': organization,
        'membership': membership,
    }
    return render(request, 'app/organization_detail.html', context)


@login_required
def team_notes(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            note = Note.objects.create(
                organization=organization,
                author=request.user,
                content=content
            )
            log_activity(organization, request.user, f"Added a note")
            return redirect('team_notes', org_id=org_id)
    
    notes = Note.objects.filter(organization=organization)
    
    context = {
        'organization': organization,
        'membership': membership,
        'notes': notes,
    }
    return render(request, 'app/team_notes.html', context)


@login_required
def delete_note(request, org_id, note_id):
    organization = get_object_or_404(Organization, id=org_id)
    note = get_object_or_404(Note, id=note_id, organization=organization)
    
    if note.author == request.user:
        log_activity(organization, request.user, f"Deleted a note")
        note.delete()
    
    return redirect('team_notes', org_id=org_id)


@login_required
def team_directory(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    members = OrganizationMember.objects.filter(organization=organization).select_related('user')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        members = members.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    context = {
        'organization': organization,
        'membership': membership,
        'members': members,
        'search_query': search_query,
    }
    return render(request, 'app/team_directory.html', context)


@login_required
def expense_tracker(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        category = request.POST.get('category')
        date = request.POST.get('date')
        description = request.POST.get('description')
        
        if amount and category and date and description:
            expense = Expense.objects.create(
                organization=organization,
                submitted_by=request.user,
                amount=amount,
                category=category,
                date=date,
                description=description
            )
            log_activity(organization, request.user, f"Submitted an expense of ${amount}")
            return redirect('expense_tracker', org_id=org_id)
    
    expenses = Expense.objects.filter(organization=organization)
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'organization': organization,
        'membership': membership,
        'expenses': expenses,
        'total_expenses': total_expenses,
    }
    return render(request, 'app/expense_tracker.html', context)


@login_required
def leave_requests(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    if request.method == 'POST':
        leave_type = request.POST.get('leave_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')
        
        if leave_type and start_date and end_date and reason:
            leave_request = LeaveRequest.objects.create(
                organization=organization,
                user=request.user,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=reason
            )
            log_activity(organization, request.user, f"Submitted a {leave_type} leave request")
            return redirect('leave_requests', org_id=org_id)
    
    leave_requests_list = LeaveRequest.objects.filter(organization=organization)
    
    context = {
        'organization': organization,
        'membership': membership,
        'leave_requests': leave_requests_list,
    }
    return render(request, 'app/leave_requests.html', context)


@login_required
def approve_leave(request, org_id, leave_id):
    organization = get_object_or_404(Organization, id=org_id)
    membership = get_object_or_404(OrganizationMember, user=request.user, organization=organization)
    
    if not membership.is_admin():
        return redirect('leave_requests', org_id=org_id)
    
    leave_request = get_object_or_404(LeaveRequest, id=leave_id, organization=organization)
    leave_request.status = 'approved'
    leave_request.reviewed_by = request.user
    leave_request.save()
    
    log_activity(organization, request.user, f"Approved leave request for {leave_request.user.username}")
    
    return redirect('leave_requests', org_id=org_id)


@login_required
def reject_leave(request, org_id, leave_id):
    organization = get_object_or_404(Organization, id=org_id)
    membership = get_object_or_404(OrganizationMember, user=request.user, organization=organization)
    
    if not membership.is_admin():
        return redirect('leave_requests', org_id=org_id)
    
    leave_request = get_object_or_404(LeaveRequest, id=leave_id, organization=organization)
    leave_request.status = 'rejected'
    leave_request.reviewed_by = request.user
    leave_request.save()
    
    log_activity(organization, request.user, f"Rejected leave request for {leave_request.user.username}")
    
    return redirect('leave_requests', org_id=org_id)


@login_required
def activity_log(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    activities = ActivityLog.objects.filter(organization=organization)[:50]
    
    context = {
        'organization': organization,
        'membership': membership,
        'activities': activities,
    }
    return render(request, 'app/activity_log.html', context)


@login_required
def data_export(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    if request.method == 'POST':
        data_type = request.POST.get('data_type')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data_type}_{organization.name}.csv"'
        
        writer = csv.writer(response)
        
        if data_type == 'members':
            writer.writerow(['Name', 'Email', 'Role', 'Joined Date'])
            members = OrganizationMember.objects.filter(organization=organization).select_related('user')
            for member in members:
                writer.writerow([
                    member.user.get_full_name() or member.user.username,
                    member.user.email,
                    member.role,
                    member.joined_at.strftime('%Y-%m-%d')
                ])
        
        elif data_type == 'expenses':
            writer.writerow(['Date', 'Category', 'Amount', 'Description', 'Submitted By'])
            expenses = Expense.objects.filter(organization=organization)
            for expense in expenses:
                writer.writerow([
                    expense.date.strftime('%Y-%m-%d'),
                    expense.category,
                    f"${expense.amount}",
                    expense.description,
                    expense.submitted_by.username
                ])
        
        elif data_type == 'leave_requests':
            writer.writerow(['User', 'Leave Type', 'Start Date', 'End Date', 'Status', 'Reason'])
            leave_requests = LeaveRequest.objects.filter(organization=organization)
            for leave in leave_requests:
                writer.writerow([
                    leave.user.username,
                    leave.leave_type,
                    leave.start_date.strftime('%Y-%m-%d'),
                    leave.end_date.strftime('%Y-%m-%d'),
                    leave.status,
                    leave.reason
                ])
        
        elif data_type == 'notes':
            writer.writerow(['Author', 'Content', 'Created At'])
            notes = Note.objects.filter(organization=organization)
            for note in notes:
                writer.writerow([
                    note.author.username,
                    note.content,
                    note.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        log_activity(organization, request.user, f"Exported {data_type} data")
        return response
    
    context = {
        'organization': organization,
        'membership': membership,
    }
    return render(request, 'app/data_export.html', context)


@login_required
def external_data(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    context = {
        'organization': organization,
        'membership': membership,
    }
    return render(request, 'app/external_data.html', context)


@login_required
def fetch_external_data(request, org_id):
    """API endpoint to fetch external data"""
    try:
        response = requests.get('https://jsonplaceholder.typicode.com/users', timeout=10)
        response.raise_for_status()
        users = response.json()
        return JsonResponse({'success': True, 'users': users})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def dashboard(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    try:
        membership = OrganizationMember.objects.get(user=request.user, organization=organization)
    except OrganizationMember.DoesNotExist:
        return redirect('home')
    
    # Widget 1: Member Count
    total_members = OrganizationMember.objects.filter(organization=organization).count()
    admin_count = OrganizationMember.objects.filter(organization=organization, role='admin').count()
    
    # Widget 2: Expense Summary
    total_expenses = Expense.objects.filter(organization=organization).aggregate(total=Sum('amount'))['total'] or 0
    expense_count = Expense.objects.filter(organization=organization).count()
    
    # Widget 3: Leave Request Status
    pending_leaves = LeaveRequest.objects.filter(organization=organization, status='pending').count()
    approved_leaves = LeaveRequest.objects.filter(organization=organization, status='approved').count()
    
    # Widget 4: Recent Activities
    recent_activities = ActivityLog.objects.filter(organization=organization)[:5]
    
    context = {
        'organization': organization,
        'membership': membership,
        'total_members': total_members,
        'admin_count': admin_count,
        'total_expenses': total_expenses,
        'expense_count': expense_count,
        'pending_leaves': pending_leaves,
        'approved_leaves': approved_leaves,
        'recent_activities': recent_activities,
    }
    return render(request, 'app/dashboard.html', context)