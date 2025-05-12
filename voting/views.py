# /home/lunge/Documents/repos/e-voting-with-django/voting/views.py

from django.shortcuts import render, redirect, reverse
from account.views import account_login
from .models import Position, Candidate, Voter, Votes
from django.http import JsonResponse
from django.utils.text import slugify
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
import requests
import json
import random as r  # Import random module

# Create your views here.

def index(request):
    if not request.user.is_authenticated:
        return account_login(request)
    # If authenticated, redirect based on user type or to dashboard
    if request.user.user_type == '1': # Admin
        return redirect(reverse('adminDashboard'))
    else: # Voter
        return redirect(reverse('voterDashboard'))
    # Fallback context (though redirection usually happens first)
    # context = {}
    # return render(request, "voting/login.html", context) # Or appropriate template

def generate_ballot(display_controls=False):
    positions = Position.objects.order_by('priority').all()
    output = ""
    candidates_data = ""
    num = 1
    # return None # This was commented out, likely not needed
    for position in positions:
        name = position.name
        position_name = slugify(name)
        candidates = Candidate.objects.filter(position=position)

        # ---- FIX: Initialize instruction before the inner loop ----
        instruction = "Select a candidate" # Default value if no candidates exist
        # ---------------------------------------------------------

        # Clear candidates_data for this position before the loop
        candidates_data = ""

        for candidate in candidates:
            if position.max_vote > 1:
                instruction = "You may select up to " + \
                    str(position.max_vote) + " candidates"
                input_box = '<input type="checkbox" value="'+str(candidate.id)+'" class="flat-red ' + \
                    position_name+'" name="' + \
                    position_name+"[]" + '">' #
            else:
                instruction = "Select only one candidate"
                input_box = '<input value="'+str(candidate.id)+'" type="radio" class="flat-red ' + \
                    position_name+'" name="'+position_name+'">' #
            image = "/media/" + str(candidate.photo)
            # Append to candidates_data for the current candidate
            candidates_data += '<li>' + input_box + '<button type="button" class="btn btn-primary btn-sm btn-flat clist platform" data-fullname="'+candidate.fullname+'" data-bio="'+candidate.bio+'"><i class="fa fa-search"></i> Platform</button><img src="' + \
                image+'" height="100px" width="100px" class="clist"><span class="cname clist">' + \
                 candidate.fullname+'</span></li>' #

        # Check if candidates_data is empty after the loop (meaning no candidates)
        if not candidates:
             candidates_data = "<li>No candidates available for this position.</li>"
             # Optionally adjust instruction if no candidates exist
             instruction = "No candidates to select for this position."


        up = ''
        if position.priority == 1:
            up = 'disabled'
        down = ''
        if position.priority == positions.count():
            down = 'disabled'

        # Construct the output HTML using the instruction variable
        output = output + f"""<div class="row">	<div class="col-xs-12"><div class="box box-solid" id="{position.id}">
            <div class="box-header with-border">
            <h3 class="box-title"><b>{name}</b></h3>""" #

        if display_controls:
            output = output + f""" <div class="pull-right box-tools">
        <button type="button" class="btn btn-default btn-sm moveup" data-id="{position.id}" {up}><i class="fa fa-arrow-up"></i> </button>
        <button type="button" class="btn btn-default btn-sm movedown" data-id="{position.id}" {down}><i class="fa fa-arrow-down"></i></button>
        </div>"""

        # Use the instruction variable here (it's guaranteed to have a value now)
        output = output + f"""</div>
        <div class="box-body">
        <p>{instruction}
        <span class="pull-right">
        <button type="button" class="btn btn-success btn-sm btn-flat reset" data-desc="{position_name}"><i class="fa fa-refresh"></i> Reset</button>
        </span>
        </p>
        <div id="candidate_list">
        <ul>
        {candidates_data}
        </ul>
        </div>
        </div>
        </div>
        </div>
        </div>
        """ #
        # Update position priority - This might be better handled elsewhere if positions can be added/deleted dynamically
        # position.priority = num
        # position.save()
        num = num + 1
        # candidates_data = '' # Already reset at the start of the outer loop

    return output


def fetch_ballot(request):
    output = generate_ballot(display_controls=True) #
    return JsonResponse(output, safe=False)


def generate_otp():
    """Link to this function
    https://www.codespeedy.com/otp-generation-using-random-module-in-python/
    """
    # import random as r # Already imported at the top
    otp = ""
    # Generate OTP of random length between 5 and 8 digits
    for i in range(r.randint(5, 8)):
        otp += str(r.randint(0, 9)) # Use 0-9 for digits
    return otp


def dashboard(request):
    user = request.user
    # Ensure user is authenticated and is a voter
    if not user.is_authenticated or user.user_type != '2':
         messages.error(request, "Access Denied.")
         return redirect(reverse('account_login'))

    voter = user.voter
    # Check if this voter has been verified
    if not voter.verified:
        # Check if OTP sending is bypassed in settings
        if not settings.SEND_OTP:
            voter.otp = "0000" # Assign default OTP if bypassing
            voter.verified = True
            voter.save()
            messages.success(request, "Account automatically verified (OTP disabled). Please cast your vote.")
            return redirect(reverse('show_ballot'))
        else:
            # Redirect to OTP verification page
            messages.warning(request, "Please verify your account via OTP.")
            return redirect(reverse('voterVerify'))
    else:
        # Voter is verified
        if voter.voted:  # Check if User has voted
            # Display election result or candidates voted for
            my_votes = Votes.objects.filter(voter=voter)
            context = {
                'my_votes': my_votes,
                'page_title': "Vote Cast"
            } #
            return render(request, "voting/voter/result.html", context)
        else:
            # Verified but hasn't voted, show the ballot
            return redirect(reverse('show_ballot'))


def verify(request):
    # Ensure user is authenticated and is a voter
    if not request.user.is_authenticated or request.user.user_type != '2':
         messages.error(request, "Access Denied.")
         return redirect(reverse('account_login'))

    # If already verified, redirect to dashboard
    if request.user.voter.verified:
        return redirect(reverse('voterDashboard'))

    context = {
        'page_title': 'OTP Verification'
    }
    return render(request, "voting/voter/verify.html", context)


def resend_otp(request): #
    """API For SMS
    Uses https://www.multitexter.com/ API to send SMS (requires environment variables).
    Toggle SEND_OTP to False in settings.py to bypass.
    """
    user = request.user
    # Ensure user is authenticated and is a voter
    if not user.is_authenticated or user.user_type != '2':
        return JsonResponse({"data": "Authentication required.", "error": True})

    voter = user.voter
    error = False
    response = ""

    if settings.SEND_OTP:
        if voter.otp_sent >= 3:
            error = True #
            response = "You have requested OTP three times. Please enter the previously sent OTP or contact support." #
        else:
            phone = voter.phone
            otp = voter.otp
            # Generate new OTP if none exists or reuse existing one for resend attempt
            if otp is None: #
                otp = generate_otp()
                voter.otp = otp
                # voter.save() # Save happens after potential successful send

            try:
                msg = f"Dear {user.first_name}, kindly use {otp} as your OTP for E-Voting." #
                message_is_sent = send_sms(phone, msg)

                if message_is_sent:
                    voter.otp_sent += 1 # Increment count only on successful send
                    voter.save() # Save OTP and incremented count
                    response = "OTP has been sent to your registered phone number." #
                else:
                    error = True
                    response = "OTP could not be sent at this time. Please try again later or contact support." #

            except Exception as e:
                error = True
                # Log the actual error e for debugging, don't show it to the user
                print(f"Error sending SMS: {e}")
                response = "An error occurred while sending OTP. Please try again." #

    else:
        # Handle OTP bypass case if needed (though verification usually handles this)
        # response = bypass_otp() # This function might be redundant here
        voter.otp = "0000" # Ensure default OTP is set
        voter.save()
        error = False
        response = "OTP sending is disabled. Please use '0000' to verify."

    return JsonResponse({"data": response, "error": error})

# This function seems redundant if bypass logic is in verify/dashboard
# def bypass_otp():
#     Voter.objects.all().filter(otp=None, verified=False).update(otp="0000", verified=True)
#     response = "Kindly cast your vote"
#     return response


def send_sms(phone_number, msg):
    """Sends SMS using MultiTexter API. Requires EMAIL and PASSWORD in env."""
    # import requests # Already imported
    import os
    # import json # Already imported

    email = os.environ.get('SMS_EMAIL')
    password = os.environ.get('SMS_PASSWORD')
    sender_name = os.environ.get('SMS_SENDER_NAME', 'E-Voting') # Default sender name

    if not email or not password:
        print("ERROR: SMS_EMAIL or SMS_PASSWORD environment variables not set.") #
        # raise Exception("SMS API Email/Password cannot be Null in environment variables")
        return False # Fail gracefully if credentials missing

    url = "https://app.multitexter.com/v2/app/sms"
    data = {"email": email, "password": password, "message": msg,
            "sender_name": sender_name, "recipients": phone_number, "forcednd": 1}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    try:
        r = requests.post(url, data=json.dumps(data), headers=headers, timeout=10) # Add timeout
        r.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
        response_data = r.json()
        status = response_data.get('status', 0)
        print(f"SMS API Response: {response_data}") # Log API response for debugging
        return str(status) == '1' #
    except requests.exceptions.RequestException as e:
        print(f"SMS API Request failed: {e}")
        return False
    except json.JSONDecodeError:
        print("Failed to decode SMS API response.")
        return False


def verify_otp(request):
    error = True
    # Ensure user is authenticated and is a voter
    if not request.user.is_authenticated or request.user.user_type != '2':
         messages.error(request, "Access Denied.")
         return redirect(reverse('account_login'))

    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect(reverse('voterVerify')) # Redirect back to verify page

    otp_entered = request.POST.get('otp')

    if not otp_entered:
        messages.error(request, "Please provide the OTP.")
    else:
        voter = request.user.voter #
        db_otp = voter.otp

        if db_otp is None:
             messages.error(request, "OTP not generated yet. Please request OTP first.")
        elif db_otp != otp_entered:
            messages.error(request, "The OTP you provided is incorrect.") #
        else:
            # OTP is correct
            messages.success(request, "Verification successful. You can now cast your vote.") #
            voter.verified = True
            voter.save()
            error = False # Mark as not an error

    if error:
        # If there was an error, stay on the verification page
        return redirect(reverse('voterVerify'))
    else:
        # If successful, redirect to the ballot page
        return redirect(reverse('show_ballot'))


def show_ballot(request):
    # Ensure user is authenticated and is a voter
    if not request.user.is_authenticated or request.user.user_type != '2':
         messages.error(request, "Access Denied.")
         return redirect(reverse('account_login'))

    voter = request.user.voter

    # Ensure voter is verified before showing ballot
    if not voter.verified:
         messages.error(request, "Please verify your account first.")
         return redirect(reverse('voterVerify'))

    if voter.voted:
        messages.error(request, "You have already cast your vote.") #
        return redirect(reverse('voterDashboard'))

    # Generate and display the ballot
    ballot_html = generate_ballot(display_controls=False)
    context = {
        'ballot': ballot_html,
        'page_title': "Cast Your Vote" # Add page title
    }
    return render(request, "voting/voter/ballot.html", context)


def preview_vote(request):
    # Ensure user is authenticated and is a voter
    if not request.user.is_authenticated or request.user.user_type != '2':
         return JsonResponse({'error': True, 'message': 'Authentication required.'})

    if request.method != 'POST':
        return JsonResponse({'error': True, 'message': 'Invalid request method.'})

    output = ""
    form = dict(request.POST)
    form.pop('csrfmiddlewaretoken', None) #

    error = False
    response_message = "" # Use message instead of list
    data_list = [] # To store structured vote data

    positions = Position.objects.order_by('priority').all() # Ensure order

    if not form: # Check if form is empty after removing CSRF
         return JsonResponse({'error': True, 'message': 'No candidates selected for preview.'})

    for position in positions:
        max_vote = position.max_vote
        pos_slug = slugify(position.name) # Use consistent slug name
        position_candidates = [] # Store names for this position

        if position.max_vote > 1:
            # Handle checkbox input (list)
            form_key = pos_slug + "[]"
            selected_ids = form.get(form_key) # This is a list

            if selected_ids: # Check if any candidate was selected for this position
                if len(selected_ids) > max_vote:
                    error = True
                    response_message += f"Error: You selected {len(selected_ids)} candidates for {position.name}, but the maximum allowed is {max_vote}.<br>" #
                    continue # Skip processing this position further in preview if error

                for candidate_id in selected_ids:
                    try:
                        candidate = Candidate.objects.get(id=candidate_id, position=position)
                        position_candidates.append(candidate.fullname)
                    except Candidate.DoesNotExist:
                        error = True
                        response_message += f"Error: Invalid candidate selected for {position.name}. Please refresh and try again.<br>" #
                        break # Stop processing this position if invalid candidate found
                if error: continue # Skip to next position if error occurred within candidate loop

        else:
            # Handle radio button input (single value)
            form_key = pos_slug
            selected_id = form.get(form_key) # This might be a list with one item

            if selected_id:
                # Ensure it's a single ID, not a list by mistake
                if isinstance(selected_id, list):
                    if len(selected_id) > 1:
                         error = True
                         response_message += f"Error: Multiple candidates selected for {position.name} (single choice position).<br>"
                         continue
                    selected_id = selected_id[0] # Take the first item if it's a list

                try:
                    candidate = Candidate.objects.get(id=selected_id, position=position)
                    position_candidates.append(candidate.fullname)
                except Candidate.DoesNotExist:
                    error = True
                    response_message += f"Error: Invalid candidate selected for {position.name}. Please refresh and try again.<br>" #
                    continue # Skip to next position

        # If candidates were found for this position, format the output
        if position_candidates:
             candidates_html = "".join([f'<li><i class="fa fa-check-square-o"></i> {name}</li>' for name in position_candidates])
             output += f"""
                <div class='row votelist' style='padding-bottom: 2px'>
                    <span class='col-sm-4'><span class='pull-right'><b>{position.name} :</b></span></span>
                    <span class='col-sm-8'>
                        <ul style='list-style-type:none; margin-left:-40px'>
                            {candidates_html}
                        </ul>
                    </span>
                </div><hr/>""" #

    # Check if any selections were made at all after processing
    if not output and not error:
         # This case might occur if form had only CSRF token initially
         error = True
         response_message = "No candidates were selected for preview."

    context = {
        'error': error,
        'list': output if not error else "", # Send preview list only if no errors
        'message': response_message # Send error messages if any
    }
    return JsonResponse(context, safe=False)


def submit_ballot(request):
    # Ensure user is authenticated and is a voter
    if not request.user.is_authenticated or request.user.user_type != '2':
         messages.error(request, "Access Denied.")
         return redirect(reverse('account_login'))

    if request.method != 'POST':
        messages.error(request, "Invalid request method.") #
        return redirect(reverse('show_ballot'))

    voter = request.user.voter

    # Ensure voter is verified
    if not voter.verified:
         messages.error(request, "Please verify your account before voting.")
         return redirect(reverse('voterVerify'))

    # Verify if the voter has voted already
    if voter.voted:
        messages.error(request, "You have already cast your vote.") #
        return redirect(reverse('voterDashboard'))

    form = dict(request.POST)
    form.pop('csrfmiddlewaretoken', None)  # Pop CSRF Token
    form.pop('submit_vote', None)  # Pop Submit Button (if present)

    # Ensure at least one selection was made
    if not form: #
        messages.error(request, "No candidates were selected. Please make your selections.") #
        return redirect(reverse('show_ballot'))

    votes_to_save = [] # Store valid votes before saving
    error_occurred = False
    form_count = 0 # Count valid selections processed

    positions = Position.objects.order_by('priority').all() #

    for position in positions:
        max_vote = position.max_vote
        pos_slug = slugify(position.name) #

        if position.max_vote > 1:
            # Handle checkboxes
            form_key = pos_slug + "[]" #
            selected_ids = form.get(form_key)

            if selected_ids: # If any selected for this position
                 form_count += len(selected_ids) # Add number selected to total count
                 if len(selected_ids) > max_vote:
                    messages.error(request, f"Error for {position.name}: You selected {len(selected_ids)} candidates, but the maximum is {max_vote}.") #
                    error_occurred = True
                    break # Stop processing immediately on validation error

                 for candidate_id in selected_ids:
                    try:
                        candidate = Candidate.objects.get(id=candidate_id, position=position)
                        # Add vote to temporary list
                        votes_to_save.append(Votes(voter=voter, position=position, candidate=candidate)) #
                    except Candidate.DoesNotExist:
                        messages.error(request, f"Error: An invalid candidate was submitted for {position.name}. Please refresh and try again.") #
                        error_occurred = True
                        break # Stop processing
                 if error_occurred: break # Exit outer loop too

        else:
            # Handle radio buttons
            form_key = pos_slug
            selected_id = form.get(form_key)

            if selected_id:
                form_count += 1 # Increment count for single selection
                # Ensure it's a single ID
                if isinstance(selected_id, list):
                     if len(selected_id) > 1:
                         messages.error(request, f"Error: Multiple candidates submitted for {position.name} (single choice position).")
                         error_occurred = True
                         break
                     selected_id = selected_id[0]

                try:
                    candidate = Candidate.objects.get(id=selected_id, position=position)
                    # Add vote to temporary list
                    votes_to_save.append(Votes(voter=voter, position=position, candidate=candidate)) #
                except Candidate.DoesNotExist:
                    messages.error(request, f"Error: An invalid candidate was submitted for {position.name}. Please refresh and try again.") #
                    error_occurred = True
                    break # Stop processing

        if error_occurred: break # Exit outer loop if error occurred in inner loop

    # After processing all positions, check if errors occurred
    if error_occurred:
        # Do not save any votes if validation failed
        return redirect(reverse('show_ballot'))
    else:
        # Validation passed, save all collected votes
        try:
            # Use bulk_create for efficiency if many votes
            # Votes.objects.bulk_create(votes_to_save)
            # Or loop save if signals or complex logic needed per save
            for vote in votes_to_save:
                 vote.save()

            # Verify count (optional sanity check)
            inserted_count = Votes.objects.filter(voter=voter).count()
            if inserted_count != len(votes_to_save): # Compare with list length, not form_count
                 # Rollback or handle discrepancy if necessary
                 Votes.objects.filter(voter=voter).delete() # Delete potentially partial votes
                 messages.error(request, "There was an issue saving your vote count. Please try again.")
                 return redirect(reverse('show_ballot'))

            # Update Voter profile to voted
            voter.voted = True
            voter.save()
            messages.success(request, "Your vote has been successfully submitted. Thank you for participating!") #
            return redirect(reverse('voterDashboard')) # Redirect to dashboard/results

        except Exception as e:
             # Catch potential database errors during save
             print(f"Error saving votes: {e}") # Log the error
             messages.error(request, "An unexpected error occurred while saving your vote. Please try again.") #
             # Consider deleting any potentially saved votes for this voter if partial save occurred
             Votes.objects.filter(voter=voter).delete()
             return redirect(reverse('show_ballot'))