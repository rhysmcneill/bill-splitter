from functools import wraps
from django.shortcuts import redirect, render
from billing.models import Bill, BillParticipant


def require_participant(view_func):
    @wraps(view_func)
    def _wrapped_view(request, uuid, *args, **kwargs):
        session_key = f"participant_{uuid}"
        participant_id = request.session.get(session_key)

        try:
            bill = Bill.objects.get(uuid=uuid)
        except Bill.DoesNotExist:
            return render(request, 'core/error/404.html', status=404)

        if not participant_id:
            return redirect("identify_participant", uuid=uuid)

        try:
            participant = BillParticipant.objects.get(id=participant_id, bill=bill)
        except BillParticipant.DoesNotExist:
            return redirect("identify_participant", uuid=uuid)

        # Attach participant to request object for convenience
        request.participant = participant

        return view_func(request, uuid, *args, **kwargs)
    return _wrapped_view
