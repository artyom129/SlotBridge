// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'SlotBridge';

  @override
  String get back => 'Back';

  @override
  String get tryAgain => 'Try again';

  @override
  String get errorCouldNotLoadData => 'Could not load data';

  @override
  String get errorGeneric => 'Something went wrong. Please try again.';

  @override
  String get errorTimeout => 'The server did not respond in time.';

  @override
  String get errorConnection =>
      'Could not connect to SlotBridge. Check your connection.';

  @override
  String get errorInvalidCredentials => 'Incorrect email or password.';

  @override
  String get errorAccessDenied => 'You do not have permission for this action.';

  @override
  String get errorNotFound => 'The requested data was not found.';

  @override
  String get errorConflict => 'The data changed. Refresh and try again.';

  @override
  String get errorCheckData => 'Check the entered data.';

  @override
  String get errorSlotUnavailable => 'This time was just booked.';

  @override
  String get errorBookingScope => 'No active branch is available for booking.';

  @override
  String get errorClientOnly => 'The mobile app is for clients.';

  @override
  String get errorNoActiveLocation => 'No branch is available for booking.';

  @override
  String get statusBooked => 'Booked';

  @override
  String get statusConfirmed => 'Confirmed';

  @override
  String get statusInProgress => 'In progress';

  @override
  String get statusCompleted => 'Completed';

  @override
  String get statusCancelled => 'Cancelled';

  @override
  String get statusNoShow => 'No show';

  @override
  String get statusUnknown => 'Unknown';

  @override
  String get welcomeTitle => 'Welcome to SlotBridge';

  @override
  String get welcomeSubtitle => 'Book and manage visits in one place.';

  @override
  String get emailLabel => 'Email';

  @override
  String get passwordLabel => 'Password';

  @override
  String get confirmPasswordLabel => 'Confirm password';

  @override
  String get showPassword => 'Show password';

  @override
  String get hidePassword => 'Hide password';

  @override
  String get enterValidEmail => 'Enter a valid email';

  @override
  String get enterEmail => 'Enter your email';

  @override
  String get enterPassword => 'Enter your password';

  @override
  String get signIn => 'Sign in';

  @override
  String get noAccountRegister => 'No account? Register';

  @override
  String get secureStorageHint =>
      'Your sign-in data is stored securely on this device.';

  @override
  String get createAccountTitle => 'Create an account';

  @override
  String get createAccountSubtitle => 'Book and manage visits in SlotBridge.';

  @override
  String get firstNameLabel => 'First name';

  @override
  String get lastNameLabel => 'Last name';

  @override
  String get phoneOptionalLabel => 'Phone (optional)';

  @override
  String get enterFirstName => 'Enter your first name';

  @override
  String get enterLastName => 'Enter your last name';

  @override
  String get max100Characters => 'Up to 100 characters';

  @override
  String get passwordMinLength => 'Password must contain at least 8 characters';

  @override
  String get passwordMaxLength => 'Password must not exceed 128 characters';

  @override
  String get repeatPassword => 'Repeat the password';

  @override
  String get passwordsDoNotMatch => 'Passwords do not match';

  @override
  String get phoneMaxLength => 'Phone must not exceed 32 characters';

  @override
  String get emailAlreadyUsed => 'This email is already in use';

  @override
  String get registrationFailed => 'Could not create the account. Try again.';

  @override
  String get accountCreatedLogin => 'Account created. Please sign in.';

  @override
  String get createAccount => 'Create account';

  @override
  String get alreadyHaveAccountLogin => 'Already have an account? Sign in';

  @override
  String get navHome => 'Home';

  @override
  String get navAppointments => 'Appointments';

  @override
  String get navProfile => 'Profile';

  @override
  String get refresh => 'Refresh';

  @override
  String helloUser(String name) {
    return 'Hello, $name!';
  }

  @override
  String get helloFallback => 'Hello!';

  @override
  String get readyForVisit => 'Ready to plan your next visit?';

  @override
  String get findConvenientTime => 'Find a convenient time';

  @override
  String get chooseServiceSpecialistSlot =>
      'Choose a service, specialist, and available time.';

  @override
  String get bookAppointment => 'Book appointment';

  @override
  String get upcoming => 'Upcoming';

  @override
  String get viewAll => 'View all';

  @override
  String get noUpcomingAppointments => 'No upcoming appointments';

  @override
  String get nextBookingAppearsHere =>
      'Your next appointment will appear here.';

  @override
  String get profile => 'Profile';

  @override
  String get client => 'Client';

  @override
  String get backend => 'Server';

  @override
  String get signOut => 'Sign out';

  @override
  String get bookingStepService => 'Service';

  @override
  String get bookingStepSpecialist => 'Specialist';

  @override
  String get bookingStepDate => 'Date';

  @override
  String get bookingStepAvailability => 'Available time';

  @override
  String get bookingStepReview => 'Confirmation';

  @override
  String get noServices => 'No services';

  @override
  String get locationHasNoServices => 'This branch has no active services.';

  @override
  String durationMinutes(int minutes) {
    return '$minutes min';
  }

  @override
  String get noSpecialist => 'No specialists available';

  @override
  String get noSpecialistForService =>
      'No specialist currently provides this service here.';

  @override
  String get availableSpecialist => 'Available for booking';

  @override
  String get noTimesOnDate => 'No available times on this date';

  @override
  String get chooseAnotherDateHint =>
      'Choose another date to find an available time.';

  @override
  String get chooseAnotherDate => 'Choose another date';

  @override
  String timesInTimezone(String timezone) {
    return 'Times are shown in $timezone';
  }

  @override
  String get serviceLabel => 'Service';

  @override
  String get specialistLabel => 'Specialist';

  @override
  String get dateLabel => 'Date';

  @override
  String get timeLabel => 'Time';

  @override
  String get locationLabel => 'Branch';

  @override
  String get noteOptional => 'Note (optional)';

  @override
  String get bookingInProgress => 'Creating appointment…';

  @override
  String get confirmBooking => 'Confirm booking';

  @override
  String get myAppointments => 'My appointments';

  @override
  String get newAppointment => 'New appointment';

  @override
  String get past => 'Past';

  @override
  String get cancelled => 'Cancelled';

  @override
  String get all => 'All';

  @override
  String get noAppointmentsInSection => 'No appointments in this section yet.';

  @override
  String get bookServiceEmptyHint =>
      'Book a service and your visit will appear here.';

  @override
  String get bookNow => 'Book now';

  @override
  String get noUpcomingSection => 'No upcoming appointments';

  @override
  String get noPastSection => 'No past appointments';

  @override
  String get noCancelledSection => 'No cancelled appointments';

  @override
  String get noAllSection => 'No appointments yet';

  @override
  String get appointmentDetails => 'Appointment details';

  @override
  String get cancelAppointmentQuestion => 'Cancel appointment?';

  @override
  String get reasonOptional => 'Reason (optional)';

  @override
  String get keepAppointment => 'Keep appointment';

  @override
  String get cancelAppointment => 'Cancel appointment';

  @override
  String get appointmentBooked => 'Booking confirmed';

  @override
  String get slotConfirmed => 'Your selected time is confirmed in SlotBridge.';

  @override
  String get timezoneLabel => 'Time zone';

  @override
  String get yourNote => 'Your note';

  @override
  String get cancellationReason => 'Cancellation reason';

  @override
  String get reschedule => 'Reschedule';

  @override
  String get updating => 'Updating…';

  @override
  String get statusHistory => 'Status history';

  @override
  String get rescheduleTitle => 'Reschedule appointment';

  @override
  String get chooseNewDate => 'Choose a new date';

  @override
  String appointmentWithSpecialist(String service, String employee) {
    return '$service, specialist — $employee';
  }

  @override
  String get availableTimes => 'Available times';

  @override
  String availableTimesOnDate(String date) {
    return 'Available times · $date';
  }

  @override
  String get noAvailableTimes => 'No available times. Choose another date.';

  @override
  String get confirmNewTime => 'Confirm new time';

  @override
  String get returnHome => 'Return home';

  @override
  String get language => 'Language';

  @override
  String get russian => 'Russian';

  @override
  String get english => 'English';

  @override
  String get theme => 'Theme';

  @override
  String get editProfile => 'Edit profile';

  @override
  String get waitlist => 'Waitlist';

  @override
  String get about => 'About SlotBridge';

  @override
  String get version => 'Version';

  @override
  String get save => 'Save';

  @override
  String get recommended => 'Recommended';

  @override
  String get allAvailableTimes => 'All available times';

  @override
  String get bestOption => 'Best option';

  @override
  String get earliestAvailable => 'Earliest available';

  @override
  String get fillsGap => 'Fills a schedule gap';
}
