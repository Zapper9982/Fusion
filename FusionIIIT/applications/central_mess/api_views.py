from datetime import date, datetime

from django.db import transaction
from django.db.models import Q, Sum
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.academic_information.models import Student
from applications.globals.models import ExtraInfo, HoldsDesignation
from .models import (
    Menu,
    MenuPoll,
    MenuPollOption,
    MenuPollVote,
    Mess_reg,
    Messinfo,
    Monthly_bill,
    Payments,
    Rebate,
    Special_request,
    Feedback,
    RegistrationRequest,
    DeregistrationRequest,
    PaymentUpdateRequest,
)
from .serializers import (
    MenuSerializer,
    MenuPollSerializer,
    MessinfoSerializer,
    MessRegSerializer,
    MonthlyBillSerializer,
    PaymentsSerializer,
    RebateSerializer,
    SpecialRequestSerializer,
    FeedbackSerializer,
    StudentSerializer,
    RegistrationRequestSerializer,
    DeregistrationRequestSerializer,
    PaymentUpdateRequestSerializer,
)


def get_student(user):
    try:
        extrainfo = ExtraInfo.objects.get(user=user)
        return Student.objects.select_related('id', 'id__user').get(id=extrainfo)
    except (ExtraInfo.DoesNotExist, Student.DoesNotExist):
        return None


def is_mess_manager(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    designations = HoldsDesignation.objects.filter(
        Q(user=user) | Q(working=user)
    ).select_related('designation')
    return any('mess' in hold.designation.name.lower() for hold in designations)


def parse_date(value, field_name):
    if not value:
        raise ValueError('{} is required'.format(field_name))
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('{} must be in YYYY-MM-DD format'.format(field_name))


def get_bill_balance(student):
    total_bill = Monthly_bill.objects.filter(student_id=student).aggregate(
        total=Sum('total_bill')
    )['total'] or 0
    total_paid = Payments.objects.filter(student_id=student, status='accept').aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    return total_bill - total_paid


def get_student_mess_option(student):
    mess_info = Messinfo.objects.filter(student_id=student).first()
    return mess_info.mess_option if mess_info else None


def get_menu_poll_queryset():
    return MenuPoll.objects.select_related('created_by').prefetch_related(
        'votes',
        'options',
        'options__votes',
    ).order_by('-created_at')


def validate_rebate_window(student, start_date, end_date):
    if start_date < date.today():
        return 'Rebate requests must be submitted before the leave start date.'

    if end_date < start_date:
        return 'End date must be on or after start date.'

    overlap = Rebate.objects.filter(
        student_id=student,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if overlap:
        return 'A rebate request already exists for the selected dates.'

    approved_days = 0
    for rebate in Rebate.objects.filter(student_id=student, status='2'):
        approved_days += (rebate.end_date - rebate.start_date).days + 1

    requested_days = (end_date - start_date).days + 1
    if approved_days + requested_days > 20:
        return 'Rebate limit exceeded. Maximum approved rebate days per semester is 20.'

    return None


def normalize_feedback_type(value):
    feedback_map = {
        'food': 'food',
        'cleanliness': 'cleanliness',
        'maintenance': 'maintenance',
        'others': 'others',
    }
    return feedback_map.get(str(value).strip().lower())


def feedback_label(value):
    label_map = {
        'food': 'Food',
        'cleanliness': 'Cleanliness',
        'maintenance': 'Maintenance',
        'others': 'Others',
        'Food': 'Food',
        'Cleanliness': 'Cleanliness',
        'Maintenance': 'Maintenance',
        'Others': 'Others',
    }
    return label_map.get(value, value)


def normalize_poll_options(options):
    if not isinstance(options, list):
        raise ValueError('Options must be provided as a list.')

    normalized = []
    seen = set()
    for option in options:
        if isinstance(option, dict):
            text = option.get('option_text') or option.get('label') or option.get('text')
        else:
            text = option
        text = str(text or '').strip()
        lowered = text.lower()
        if not text or lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(text)

    if len(normalized) < 2:
        raise ValueError('At least two unique poll options are required.')

    return normalized


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def menu_api(request):
    if request.method == 'PUT':
        if not is_mess_manager(request.user):
            return Response({'error': 'Only mess managers can update the menu.'},
                            status=status.HTTP_403_FORBIDDEN)

        mess_option = request.data.get('mess_option')
        entries = request.data.get('entries', [])
        if mess_option not in {'mess1', 'mess2'}:
            return Response({'message': 'Select a valid mess option.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(entries, list) or not entries:
            return Response({'message': 'Menu entries are required.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for entry in entries:
                meal_time = entry.get('meal_time')
                dish = str(entry.get('dish', '')).strip()
                if not meal_time or not dish:
                    continue
                Menu.objects.update_or_create(
                    mess_option=mess_option,
                    meal_time=meal_time,
                    defaults={'dish': dish},
                )

        menu = Menu.objects.filter(mess_option=mess_option)
        return Response({
            'message': 'Menu updated successfully.',
            'payload': MenuSerializer(menu, many=True).data,
        }, status=status.HTTP_200_OK)

    student = get_student(request.user)
    if student:
        mess_info = Messinfo.objects.filter(student_id=student).first()
        mess_option = mess_info.mess_option if mess_info else 'mess2'
        menu = Menu.objects.filter(mess_option=mess_option)
        serializer = MenuSerializer(menu, many=True)
        return Response({
            'payload': serializer.data,
            'mess_option': mess_option,
        }, status=status.HTTP_200_OK)

    if is_mess_manager(request.user):
        menu = Menu.objects.all()
        serializer = MenuSerializer(menu, many=True)
        return Response({
            'payload': serializer.data,
            'mess_option': None,
        }, status=status.HTTP_200_OK)

    return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def menu_poll_api(request):
    student = get_student(request.user)
    student_mess_option = get_student_mess_option(student) if student else None

    if request.method == 'GET':
        if student:
            queryset = get_menu_poll_queryset().filter(mess_option=student_mess_option) if student_mess_option else MenuPoll.objects.none()
            serializer = MenuPollSerializer(
                queryset, many=True,
                context={
                    'student': student,
                    'student_mess_option': student_mess_option,
                }
            )
            return Response({
                'payload': serializer.data,
                'mess_option': student_mess_option,
            }, status=status.HTTP_200_OK)

        if is_mess_manager(request.user):
            serializer = MenuPollSerializer(get_menu_poll_queryset(), many=True)
            return Response({'payload': serializer.data}, status=status.HTTP_200_OK)

        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        if not is_mess_manager(request.user):
            return Response({'error': 'Only mess managers can create menu polls.'},
                            status=status.HTTP_403_FORBIDDEN)

        question = str(request.data.get('question', '')).strip()
        description = str(request.data.get('description', '')).strip()
        mess_option = request.data.get('mess_option')
        meal_time = request.data.get('meal_time') or None
        poll_date_value = request.data.get('poll_date') or None
        poll_status = request.data.get('status', 'open')

        if not question:
            return Response({'message': 'Poll question is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if mess_option not in {'mess1', 'mess2'}:
            return Response({'message': 'Select a valid mess option.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if meal_time and meal_time not in dict(Menu._meta.get_field('meal_time').choices):
            return Response({'message': 'Select a valid meal time.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if poll_status not in {'open', 'closed'}:
            return Response({'message': 'Status must be open or closed.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            options = normalize_poll_options(request.data.get('options', []))
        except ValueError as exc:
            return Response({'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        poll_date = None
        if poll_date_value:
            try:
                poll_date = parse_date(poll_date_value, 'poll_date')
            except ValueError as exc:
                return Response({'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            poll = MenuPoll.objects.create(
                question=question,
                description=description,
                mess_option=mess_option,
                meal_time=meal_time,
                poll_date=poll_date,
                status=poll_status,
                created_by=request.user,
            )
            MenuPollOption.objects.bulk_create([
                MenuPollOption(
                    poll=poll,
                    option_text=option_text,
                    display_order=index,
                )
                for index, option_text in enumerate(options)
            ])

        poll = get_menu_poll_queryset().filter(id=poll.id).first()
        serializer = MenuPollSerializer(poll)
        return Response({
            'message': 'Menu poll created successfully.',
            'payload': serializer.data,
        }, status=status.HTTP_201_CREATED)

    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can update menu polls.'},
                        status=status.HTTP_403_FORBIDDEN)

    poll = MenuPoll.objects.filter(id=request.data.get('id')).first()
    if not poll:
        return Response({'error': 'Menu poll not found.'}, status=status.HTTP_404_NOT_FOUND)

    updated_fields = []

    if 'question' in request.data:
        poll.question = str(request.data.get('question', '')).strip()
        if not poll.question:
            return Response({'message': 'Poll question is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        updated_fields.append('question')

    if 'description' in request.data:
        poll.description = str(request.data.get('description', '')).strip()
        updated_fields.append('description')

    if 'status' in request.data:
        poll_status = request.data.get('status')
        if poll_status not in {'open', 'closed'}:
            return Response({'message': 'Status must be open or closed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        poll.status = poll_status
        updated_fields.append('status')

    if 'meal_time' in request.data:
        meal_time = request.data.get('meal_time') or None
        if meal_time and meal_time not in dict(Menu._meta.get_field('meal_time').choices):
            return Response({'message': 'Select a valid meal time.'},
                            status=status.HTTP_400_BAD_REQUEST)
        poll.meal_time = meal_time
        updated_fields.append('meal_time')

    if 'poll_date' in request.data:
        poll_date_value = request.data.get('poll_date')
        if poll_date_value:
            try:
                poll.poll_date = parse_date(poll_date_value, 'poll_date')
            except ValueError as exc:
                return Response({'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            poll.poll_date = None
        updated_fields.append('poll_date')

    if 'options' in request.data:
        return Response({
            'message': 'Poll options cannot be edited after creation. Create a new poll instead.'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not updated_fields:
        return Response({'message': 'No changes were provided.'},
                        status=status.HTTP_400_BAD_REQUEST)

    updated_fields.append('updated_at')
    poll.save(update_fields=updated_fields)

    poll = get_menu_poll_queryset().filter(id=poll.id).first()
    serializer = MenuPollSerializer(poll)
    return Response({
        'message': 'Menu poll updated successfully.',
        'payload': serializer.data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def menu_poll_vote_api(request):
    student = get_student(request.user)
    if not student:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    poll = get_menu_poll_queryset().filter(id=request.data.get('poll_id')).first()
    if not poll:
        return Response({'error': 'Menu poll not found.'}, status=status.HTTP_404_NOT_FOUND)

    if poll.status != 'open':
        return Response({'message': 'Voting is closed for this poll.'},
                        status=status.HTTP_400_BAD_REQUEST)

    student_mess_option = get_student_mess_option(student)
    if student_mess_option != poll.mess_option:
        return Response({
            'message': 'You can vote only for polls created for your registered mess.'
        }, status=status.HTTP_403_FORBIDDEN)

    option = poll.options.filter(id=request.data.get('option_id')).first()
    if not option:
        return Response({'message': 'Select a valid poll option.'},
                        status=status.HTTP_400_BAD_REQUEST)

    vote, created = MenuPollVote.objects.update_or_create(
        poll=poll,
        student_id=student,
        defaults={'option': option},
    )

    poll = get_menu_poll_queryset().filter(id=poll.id).first()
    serializer = MenuPollSerializer(
        poll,
        context={
            'student': student,
            'student_mess_option': student_mess_option,
        }
    )
    return Response({
        'message': 'Vote submitted successfully.' if created else 'Vote updated successfully.',
        'payload': serializer.data,
        'vote_id': vote.id,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_registration_status_api(request):
    student = get_student(request.user)
    if not student:
        return Response({
            'payload': {
                'isRegistered': False,
                'current_mess_status': 'Not Found',
                'current_rem_balance': 0,
            }
        }, status=status.HTTP_200_OK)

    mess_info = Messinfo.objects.filter(student_id=student).first()
    is_registered = mess_info is not None
    return Response({
        'payload': {
            'isRegistered': is_registered,
            'mess_option': mess_info.mess_option if mess_info else None,
            'current_mess_status': 'Registered' if is_registered else 'Deregistered',
            'current_rem_balance': get_bill_balance(student),
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def registration_request_api(request):
    student = get_student(request.user)

    if request.method == 'GET':
        if is_mess_manager(request.user):
            queryset = RegistrationRequest.objects.select_related(
                'student_id', 'student_id__id', 'student_id__id__user'
            )
        else:
            if not student:
                return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
            queryset = RegistrationRequest.objects.filter(student_id=student)
        serializer = RegistrationRequestSerializer(queryset, many=True)
        return Response({'payload': serializer.data}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        if not student:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        mess_option = request.data.get('mess_option')
        start_date = parse_date(request.data.get('start_date'), 'start_date')
        payment_date = parse_date(request.data.get('payment_date'), 'payment_date')
        amount = int(request.data.get('amount', request.data.get('amount_paid', 0)) or 0)
        txn_no = request.data.get('Txn_no') or request.data.get('txn_no')
        receipt = request.FILES.get('img') if hasattr(request, 'FILES') else None

        if mess_option not in {'mess1', 'mess2'}:
            return Response({'message': 'Select a valid mess option.'}, status=status.HTTP_400_BAD_REQUEST)
        if not txn_no:
            return Response({'message': 'Transaction number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        current_window = Mess_reg.objects.order_by('-id').first()
        if current_window and not (current_window.start_reg <= date.today() <= current_window.end_reg):
            return Response({'message': 'Registration portal is closed.'}, status=status.HTTP_400_BAD_REQUEST)

        existing_pending = RegistrationRequest.objects.filter(
            student_id=student, status='pending'
        ).exists()
        if existing_pending:
            return Response({'message': 'A registration request is already pending.'},
                            status=status.HTTP_400_BAD_REQUEST)

        registration = RegistrationRequest.objects.create(
            student_id=student,
            mess_option=mess_option,
            start_date=start_date,
            payment_date=payment_date,
            amount=amount,
            Txn_no=txn_no,
            img=receipt,
            registration_remark=request.data.get('registration_remark', ''),
        )
        return Response({
            'message': 'Registration request submitted successfully.',
            'payload': RegistrationRequestSerializer(registration).data,
        }, status=status.HTTP_201_CREATED)

    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can process registration requests.'},
                        status=status.HTTP_403_FORBIDDEN)

    request_id = request.data.get('id')
    reg_request = RegistrationRequest.objects.filter(id=request_id).select_related(
        'student_id'
    ).first()
    if not reg_request:
        return Response({'error': 'Registration request not found.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if new_status not in {'accept', 'reject'}:
        return Response({'message': 'Status must be accept or reject.'},
                        status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        reg_request.status = new_status
        reg_request.registration_remark = request.data.get(
            'registration_remark', reg_request.registration_remark
        )
        reg_request.mess_option = request.data.get('mess_option', reg_request.mess_option)
        reg_request.save()

        if new_status == 'accept':
            Messinfo.objects.update_or_create(
                student_id=reg_request.student_id,
                defaults={'mess_option': reg_request.mess_option},
            )
            mess_reg = Mess_reg.objects.order_by('-id').first()
            payment_year = reg_request.payment_date.year
            Payments.objects.update_or_create(
                student_id=reg_request.student_id,
                sem=mess_reg.sem if mess_reg else reg_request.student_id.curr_semester_no,
                year=payment_year,
                defaults={
                    'amount_paid': reg_request.amount,
                    'payment_date': reg_request.payment_date,
                    'payment_month': reg_request.payment_date.strftime('%B'),
                    'payment_year': payment_year,
                    'Txn_no': reg_request.Txn_no,
                    'status': 'accept',
                }
            )

    return Response({'message': 'Registration request updated successfully.'},
                    status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_student_bill_api(request):
    target_student = get_student(request.user)
    if request.method == 'POST' and is_mess_manager(request.user):
        requested_student = request.data.get('student_id')
        if requested_student:
            target_student = Student.objects.filter(id=requested_student).first()

    if not target_student:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    bills = Monthly_bill.objects.filter(student_id=target_student).order_by('-year', '-id')
    serializer = MonthlyBillSerializer(bills, many=True)
    return Response({'payload': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def rebate_api(request):
    student = get_student(request.user)

    if request.method == 'GET':
        queryset = Rebate.objects.all() if is_mess_manager(request.user) else Rebate.objects.filter(student_id=student)
        serializer = RebateSerializer(queryset.order_by('-app_date', '-id'), many=True)
        return Response({'payload': serializer.data}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        if not student:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        start_date = parse_date(request.data.get('start_date'), 'start_date')
        end_date = parse_date(request.data.get('end_date'), 'end_date')
        purpose = request.data.get('purpose', '').strip()
        if not purpose:
            return Response({'message': 'Purpose is required.'}, status=status.HTTP_400_BAD_REQUEST)

        validation_error = validate_rebate_window(student, start_date, end_date)
        if validation_error:
            return Response({'status': 3, 'message': validation_error}, status=status.HTTP_400_BAD_REQUEST)

        rebate = Rebate.objects.create(
            student_id=student,
            start_date=start_date,
            end_date=end_date,
            purpose=purpose,
            leave_type=request.data.get('leave_type', 'casual'),
            status='1',
            app_date=date.today(),
        )
        return Response({
            'message': 'Rebate applied successfully',
            'payload': RebateSerializer(rebate).data,
        }, status=status.HTTP_201_CREATED)

    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can process rebate requests.'},
                        status=status.HTTP_403_FORBIDDEN)

    rebate = Rebate.objects.filter(id=request.data.get('id')).first()
    if not rebate:
        return Response({'error': 'Rebate request not found'}, status=status.HTTP_404_NOT_FOUND)

    new_status = str(request.data.get('status'))
    if new_status not in {'0', '2'}:
        return Response({'message': 'Status must be 0 or 2.'}, status=status.HTTP_400_BAD_REQUEST)

    rebate.status = new_status
    rebate.rebate_remark = request.data.get('rebate_remark', rebate.rebate_remark)
    rebate.save(update_fields=['status', 'rebate_remark'])
    return Response({'message': 'Rebate request updated.'}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def special_request_api(request):
    student = get_student(request.user)

    if request.method == 'GET':
        queryset = Special_request.objects.all() if is_mess_manager(request.user) else Special_request.objects.filter(student_id=student)
        serializer = SpecialRequestSerializer(queryset.order_by('-app_date', '-id'), many=True)
        return Response({'payload': serializer.data}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        if not student:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        start_date = parse_date(request.data.get('start_date'), 'start_date')
        end_date = parse_date(request.data.get('end_date'), 'end_date')
        if end_date < start_date:
            return Response({'message': 'End date must be on or after start date.'},
                            status=status.HTTP_400_BAD_REQUEST)

        item1 = request.data.get('item1', '').strip()
        item2 = request.data.get('item2', '').strip()
        purpose = request.data.get('request') or request.data.get('purpose', '')
        purpose = purpose.strip()
        if not item1 or not item2 or not purpose:
            return Response({'message': 'Food, timing, and reason are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        special_request = Special_request.objects.create(
            student_id=student,
            start_date=start_date,
            end_date=end_date,
            item1=item1,
            item2=item2,
            request=purpose,
            status='1',
            app_date=date.today(),
        )
        return Response({
            'message': 'Special food request submitted.',
            'payload': SpecialRequestSerializer(special_request).data,
        }, status=status.HTTP_201_CREATED)

    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can process special food requests.'},
                        status=status.HTTP_403_FORBIDDEN)

    special_request = Special_request.objects.filter(id=request.data.get('id')).first()
    if not special_request:
        return Response({'error': 'Special food request not found'}, status=status.HTTP_404_NOT_FOUND)

    new_status = str(request.data.get('status'))
    if new_status not in {'0', '2'}:
        return Response({'message': 'Status must be 0 or 2.'}, status=status.HTTP_400_BAD_REQUEST)

    special_request.status = new_status
    special_request.special_request_remark = request.data.get(
        'special_request_remark', special_request.special_request_remark
    )
    special_request.save(update_fields=['status', 'special_request_remark'])
    return Response({'message': 'Special food request updated.'}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def feedback_api(request):
    student = get_student(request.user)

    if request.method == 'GET':
        queryset = Feedback.objects.all() if is_mess_manager(request.user) else Feedback.objects.filter(student_id=student)
        serializer = FeedbackSerializer(queryset.order_by('-fdate', '-id'), many=True)
        payload = serializer.data
        for item in payload:
            item['feedback_type'] = feedback_label(item['feedback_type'])
        return Response({'payload': payload}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        if not student:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        description = request.data.get('description', '').strip()
        if not description:
            return Response({'message': 'Feedback description cannot be empty.'},
                            status=status.HTTP_400_BAD_REQUEST)

        feedback_type = normalize_feedback_type(request.data.get('feedback_type'))
        if not feedback_type:
            return Response({'message': 'Select a valid feedback type.'},
                            status=status.HTTP_400_BAD_REQUEST)

        mess_info = Messinfo.objects.filter(student_id=student).first()
        feedback = Feedback.objects.create(
            student_id=student,
            mess=mess_info.mess_option if mess_info else 'mess2',
            mess_rating=int(request.data.get('mess_rating', 5)),
            fdate=date.today(),
            description=description,
            feedback_type=feedback_label(feedback_type),
        )
        return Response({
            'message': 'Feedback submitted.',
            'payload': FeedbackSerializer(feedback).data,
        }, status=status.HTTP_200_OK)

    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can update feedback state.'},
                        status=status.HTTP_403_FORBIDDEN)

    normalized_type = normalize_feedback_type(request.data.get('feedback_type'))
    feedback_type_values = []
    if normalized_type:
        feedback_type_values.extend([normalized_type, feedback_label(normalized_type)])
    raw_feedback_type = request.data.get('feedback_type')
    if raw_feedback_type:
        feedback_type_values.append(str(raw_feedback_type).strip())

    feedback = Feedback.objects.filter(
        student_id__id__user__username=request.data.get('student_id'),
        mess=request.data.get('mess'),
        feedback_type__in=feedback_type_values or [raw_feedback_type],
        description=request.data.get('description'),
        fdate=request.data.get('fdate'),
    ).first()
    if not feedback:
        return Response({'error': 'Feedback not found.'}, status=status.HTTP_404_NOT_FOUND)

    feedback.is_read = True
    feedback.save(update_fields=['is_read'])
    return Response({'message': 'Feedback marked as read.'}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payments_api(request):
    student = get_student(request.user)
    if not student:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        payment_date = parse_date(request.data.get('payment_date'), 'payment_date')
        amount_paid = int(request.data.get('amount_paid', 0) or 0)
        payment_month = request.data.get('payment_month') or payment_date.strftime('%B')
        payment_year = int(request.data.get('payment_year', payment_date.year))
        sem = int(request.data.get('sem', student.curr_semester_no))

        payment = Payments.objects.create(
            student_id=student,
            sem=sem,
            year=payment_year,
            amount_paid=amount_paid,
            payment_date=payment_date,
            payment_month=payment_month,
            payment_year=payment_year,
            Txn_no=request.data.get('Txn_no', ''),
            status='accept',
        )
        return Response({
            'message': 'Payment details submitted.',
            'payload': PaymentsSerializer(payment).data,
        }, status=status.HTTP_201_CREATED)

    payments = Payments.objects.filter(student_id=student).order_by('-payment_year', '-payment_date', '-id')
    serializer = PaymentsSerializer(payments, many=True)
    return Response({'payload': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_mess_students_api(request):
    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can access registration data.'},
                        status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        mess_infos = Messinfo.objects.select_related('student_id', 'student_id__id', 'student_id__id__user')
        serializer = MessinfoSerializer(mess_infos, many=True)
        return Response({'payload': serializer.data}, status=status.HTTP_200_OK)

    request_type = request.data.get('type')
    if request_type == 'search':
        username = str(request.data.get('student_id', '')).upper()
        student = Student.objects.select_related('id', 'id__user').filter(
            id__user__username=username
        ).first()
        if not student:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        mess_info = Messinfo.objects.filter(student_id=student).first()
        return Response({
            'payload': {
                'id': student.id_id,
                'first_name': student.id.user.first_name,
                'last_name': student.id.user.last_name,
                'student_id': student.id.user.username,
                'program': student.programme,
                'mess_option': mess_info.mess_option if mess_info else '-',
                'current_mess_status': 'Registered' if mess_info else 'Deregistered',
            }
        }, status=status.HTTP_200_OK)

    queryset = Student.objects.select_related('id', 'id__user')
    status_filter = str(request.data.get('status', 'all')).lower()
    programme_filter = request.data.get('program', 'all')
    mess_option_filter = str(request.data.get('mess_option', 'all')).lower()

    if programme_filter != 'all':
        queryset = queryset.filter(programme=programme_filter)

    payload = []
    for student in queryset:
        mess_info = Messinfo.objects.filter(student_id=student).first()
        current_status = 'Registered' if mess_info else 'Deregistered'
        if status_filter != 'all' and current_status.lower() != status_filter.lower():
            continue
        if mess_option_filter not in {'all', ''} and (not mess_info or mess_info.mess_option != mess_option_filter):
            continue
        payload.append({
            'id': student.id_id,
            'first_name': student.id.user.first_name,
            'last_name': student.id.user.last_name,
            'student_id': student.id.user.username,
            'program': student.programme,
            'mess_option': mess_info.mess_option if mess_info else '-',
            'current_mess_status': current_status,
        })

    return Response({'payload': payload}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def deregistration_request_api(request):
    student = get_student(request.user)

    if request.method == 'GET':
        queryset = DeregistrationRequest.objects.all() if is_mess_manager(request.user) else DeregistrationRequest.objects.filter(student_id=student)
        serializer = DeregistrationRequestSerializer(queryset.order_by('-created_at'), many=True)
        return Response({'payload': serializer.data}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        if not student:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        if not Messinfo.objects.filter(student_id=student).exists():
            return Response({'message': 'Student is not currently registered in mess.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if get_bill_balance(student) > 0:
            return Response({'message': 'Deregistration is allowed only after clearing pending dues.'},
                            status=status.HTTP_400_BAD_REQUEST)

        end_date = parse_date(request.data.get('end_date'), 'end_date')
        if end_date < date.today().replace(day=1):
            return Response({'message': 'Select a valid deregistration end date.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if DeregistrationRequest.objects.filter(student_id=student, status='pending').exists():
            return Response({'message': 'A deregistration request is already pending.'},
                            status=status.HTTP_400_BAD_REQUEST)

        dereg_request = DeregistrationRequest.objects.create(
            student_id=student,
            end_date=end_date,
            deregistration_remark=request.data.get('deregistration_remark', ''),
        )
        return Response({
            'message': 'Deregistration request submitted successfully.',
            'payload': DeregistrationRequestSerializer(dereg_request).data,
        }, status=status.HTTP_201_CREATED)

    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can process deregistration requests.'},
                        status=status.HTTP_403_FORBIDDEN)

    dereg_request = DeregistrationRequest.objects.filter(id=request.data.get('id')).select_related('student_id').first()
    if not dereg_request:
        return Response({'error': 'Deregistration request not found.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if new_status not in {'accept', 'reject'}:
        return Response({'message': 'Status must be accept or reject.'},
                        status=status.HTTP_400_BAD_REQUEST)

    dereg_request.status = new_status
    dereg_request.deregistration_remark = request.data.get(
        'deregistration_remark', dereg_request.deregistration_remark
    )
    dereg_request.save()
    if new_status == 'accept':
        Messinfo.objects.filter(student_id=dereg_request.student_id).delete()

    return Response({'message': 'Deregistration request updated successfully.'},
                    status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def update_payment_request_api(request):
    student = get_student(request.user)

    if request.method == 'POST':
        if not student:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        payment_date = parse_date(request.data.get('payment_date'), 'payment_date')
        amount = int(request.data.get('amount', 0) or 0)
        txn_no = request.data.get('Txn_no') or request.data.get('txn_no')
        receipt = request.FILES.get('img') if hasattr(request, 'FILES') else None
        if not txn_no:
            return Response({'message': 'Transaction number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        payment_request = PaymentUpdateRequest.objects.create(
            student_id=student,
            payment_date=payment_date,
            amount=amount,
            Txn_no=txn_no,
            img=receipt,
            update_remark=request.data.get('update_remark', ''),
        )
        return Response({
            'message': 'Payment update request submitted.',
            'payload': PaymentUpdateRequestSerializer(payment_request).data,
        }, status=status.HTTP_201_CREATED)

    if request.method == 'GET':
        queryset = PaymentUpdateRequest.objects.all() if is_mess_manager(request.user) else PaymentUpdateRequest.objects.filter(student_id=student)
        query_student = request.query_params.get('student_id')
        if query_student and not is_mess_manager(request.user):
            queryset = queryset.filter(student_id__id__user__username=query_student)
        serializer = PaymentUpdateRequestSerializer(queryset.order_by('-created_at'), many=True)
        return Response({'payload': serializer.data}, status=status.HTTP_200_OK)

    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can process payment update requests.'},
                        status=status.HTTP_403_FORBIDDEN)

    payment_request = PaymentUpdateRequest.objects.filter(id=request.data.get('id')).select_related('student_id').first()
    if not payment_request:
        return Response({'error': 'Payment update request not found.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if new_status not in {'accept', 'reject'}:
        return Response({'message': 'Status must be accept or reject.'},
                        status=status.HTTP_400_BAD_REQUEST)

    payment_request.status = new_status
    payment_request.update_remark = request.data.get('update_payment_remark', request.data.get('update_remark', payment_request.update_remark))
    payment_request.save()

    if new_status == 'accept':
        payment_year = payment_request.payment_date.year
        Payments.objects.create(
            student_id=payment_request.student_id,
            sem=payment_request.student_id.curr_semester_no,
            year=payment_year,
            amount_paid=payment_request.amount,
            payment_date=payment_request.payment_date,
            payment_month=payment_request.payment_date.strftime('%B'),
            payment_year=payment_year,
            Txn_no=payment_request.Txn_no,
            status='accept',
        )

    return Response({'message': 'Payment update request updated.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mess_reg_api(request):
    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can update registration dates.'},
                        status=status.HTTP_403_FORBIDDEN)

    sem = request.data.get('sem', 1)
    start_value = request.data.get('start_date') or request.data.get('start_reg')
    end_value = request.data.get('end_date') or request.data.get('end_reg')
    start_date = parse_date(start_value, 'start_date')
    end_date = parse_date(end_value, 'end_date')
    if end_date <= start_date:
        return Response({'message': 'End date must be greater than start date.'},
                        status=status.HTTP_400_BAD_REQUEST)

    reg = Mess_reg.objects.create(sem=sem, start_reg=start_date, end_reg=end_date)
    return Response({
        'message': 'Registration dates updated.',
        'payload': MessRegSerializer(reg).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mess_balance_status_api(request):
    if not is_mess_manager(request.user):
        return Response({'error': 'Only mess managers can view mess balance status.'},
                        status=status.HTTP_403_FORBIDDEN)

    bills = Monthly_bill.objects.select_related('student_id', 'student_id__id', 'student_id__id__user').all()
    serializer = MonthlyBillSerializer(bills, many=True)
    return Response({'payload': serializer.data}, status=status.HTTP_200_OK)
