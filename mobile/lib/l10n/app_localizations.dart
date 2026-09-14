import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ru.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[Locale('ru')];

  /// No description provided for @appTitle.
  ///
  /// In ru, this message translates to:
  /// **'SlotBridge'**
  String get appTitle;

  /// No description provided for @back.
  ///
  /// In ru, this message translates to:
  /// **'Назад'**
  String get back;

  /// No description provided for @tryAgain.
  ///
  /// In ru, this message translates to:
  /// **'Повторить'**
  String get tryAgain;

  /// No description provided for @errorCouldNotLoadData.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось загрузить данные'**
  String get errorCouldNotLoadData;

  /// No description provided for @errorGeneric.
  ///
  /// In ru, this message translates to:
  /// **'Что-то пошло не так. Попробуйте ещё раз.'**
  String get errorGeneric;

  /// No description provided for @errorTimeout.
  ///
  /// In ru, this message translates to:
  /// **'Сервер не ответил вовремя. Попробуйте ещё раз.'**
  String get errorTimeout;

  /// No description provided for @errorConnection.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось подключиться к SlotBridge. Проверьте адрес сервера и подключение.'**
  String get errorConnection;

  /// No description provided for @errorInvalidCredentials.
  ///
  /// In ru, this message translates to:
  /// **'Неверная электронная почта или пароль.'**
  String get errorInvalidCredentials;

  /// No description provided for @errorAccessDenied.
  ///
  /// In ru, this message translates to:
  /// **'Недостаточно прав для этого действия.'**
  String get errorAccessDenied;

  /// No description provided for @errorNotFound.
  ///
  /// In ru, this message translates to:
  /// **'Запрошенные данные не найдены.'**
  String get errorNotFound;

  /// No description provided for @errorConflict.
  ///
  /// In ru, this message translates to:
  /// **'Данные изменились. Обновите экран и попробуйте ещё раз.'**
  String get errorConflict;

  /// No description provided for @errorCheckData.
  ///
  /// In ru, this message translates to:
  /// **'Проверьте введённые данные.'**
  String get errorCheckData;

  /// No description provided for @errorSlotUnavailable.
  ///
  /// In ru, this message translates to:
  /// **'Это время уже занято. Выберите другой вариант.'**
  String get errorSlotUnavailable;

  /// No description provided for @errorBookingScope.
  ///
  /// In ru, this message translates to:
  /// **'Для записи недоступен активный филиал.'**
  String get errorBookingScope;

  /// No description provided for @errorClientOnly.
  ///
  /// In ru, this message translates to:
  /// **'Мобильное приложение предназначено для клиентов.'**
  String get errorClientOnly;

  /// No description provided for @errorNoActiveLocation.
  ///
  /// In ru, this message translates to:
  /// **'Нет доступного филиала для записи.'**
  String get errorNoActiveLocation;

  /// No description provided for @statusBooked.
  ///
  /// In ru, this message translates to:
  /// **'Запланирована'**
  String get statusBooked;

  /// No description provided for @statusConfirmed.
  ///
  /// In ru, this message translates to:
  /// **'Подтверждена'**
  String get statusConfirmed;

  /// No description provided for @statusInProgress.
  ///
  /// In ru, this message translates to:
  /// **'Выполняется'**
  String get statusInProgress;

  /// No description provided for @statusCompleted.
  ///
  /// In ru, this message translates to:
  /// **'Завершена'**
  String get statusCompleted;

  /// No description provided for @statusCancelled.
  ///
  /// In ru, this message translates to:
  /// **'Отменена'**
  String get statusCancelled;

  /// No description provided for @statusNoShow.
  ///
  /// In ru, this message translates to:
  /// **'Неявка'**
  String get statusNoShow;

  /// No description provided for @statusUnknown.
  ///
  /// In ru, this message translates to:
  /// **'Неизвестно'**
  String get statusUnknown;

  /// No description provided for @welcomeTitle.
  ///
  /// In ru, this message translates to:
  /// **'Добро пожаловать в SlotBridge'**
  String get welcomeTitle;

  /// No description provided for @welcomeSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Записывайтесь и управляйте визитами в одном месте.'**
  String get welcomeSubtitle;

  /// No description provided for @emailLabel.
  ///
  /// In ru, this message translates to:
  /// **'Электронная почта'**
  String get emailLabel;

  /// No description provided for @passwordLabel.
  ///
  /// In ru, this message translates to:
  /// **'Пароль'**
  String get passwordLabel;

  /// No description provided for @confirmPasswordLabel.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердите пароль'**
  String get confirmPasswordLabel;

  /// No description provided for @showPassword.
  ///
  /// In ru, this message translates to:
  /// **'Показать пароль'**
  String get showPassword;

  /// No description provided for @hidePassword.
  ///
  /// In ru, this message translates to:
  /// **'Скрыть пароль'**
  String get hidePassword;

  /// No description provided for @enterValidEmail.
  ///
  /// In ru, this message translates to:
  /// **'Введите корректную электронную почту'**
  String get enterValidEmail;

  /// No description provided for @enterEmail.
  ///
  /// In ru, this message translates to:
  /// **'Введите электронную почту'**
  String get enterEmail;

  /// No description provided for @enterPassword.
  ///
  /// In ru, this message translates to:
  /// **'Введите пароль'**
  String get enterPassword;

  /// No description provided for @signIn.
  ///
  /// In ru, this message translates to:
  /// **'Войти'**
  String get signIn;

  /// No description provided for @noAccountRegister.
  ///
  /// In ru, this message translates to:
  /// **'Нет аккаунта? Зарегистрироваться'**
  String get noAccountRegister;

  /// No description provided for @secureStorageHint.
  ///
  /// In ru, this message translates to:
  /// **'Данные авторизации надёжно хранятся в защищённом хранилище устройства.'**
  String get secureStorageHint;

  /// No description provided for @createAccountTitle.
  ///
  /// In ru, this message translates to:
  /// **'Создайте аккаунт'**
  String get createAccountTitle;

  /// No description provided for @createAccountSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Записывайтесь и управляйте визитами в SlotBridge.'**
  String get createAccountSubtitle;

  /// No description provided for @firstNameLabel.
  ///
  /// In ru, this message translates to:
  /// **'Имя'**
  String get firstNameLabel;

  /// No description provided for @lastNameLabel.
  ///
  /// In ru, this message translates to:
  /// **'Фамилия'**
  String get lastNameLabel;

  /// No description provided for @phoneOptionalLabel.
  ///
  /// In ru, this message translates to:
  /// **'Телефон (необязательно)'**
  String get phoneOptionalLabel;

  /// No description provided for @enterFirstName.
  ///
  /// In ru, this message translates to:
  /// **'Введите имя'**
  String get enterFirstName;

  /// No description provided for @enterLastName.
  ///
  /// In ru, this message translates to:
  /// **'Введите фамилию'**
  String get enterLastName;

  /// No description provided for @max100Characters.
  ///
  /// In ru, this message translates to:
  /// **'Не больше 100 символов'**
  String get max100Characters;

  /// No description provided for @passwordMinLength.
  ///
  /// In ru, this message translates to:
  /// **'Пароль должен содержать минимум 8 символов'**
  String get passwordMinLength;

  /// No description provided for @passwordMaxLength.
  ///
  /// In ru, this message translates to:
  /// **'Пароль должен быть не длиннее 128 символов'**
  String get passwordMaxLength;

  /// No description provided for @repeatPassword.
  ///
  /// In ru, this message translates to:
  /// **'Повторите пароль'**
  String get repeatPassword;

  /// No description provided for @passwordsDoNotMatch.
  ///
  /// In ru, this message translates to:
  /// **'Пароли не совпадают'**
  String get passwordsDoNotMatch;

  /// No description provided for @phoneMaxLength.
  ///
  /// In ru, this message translates to:
  /// **'Телефон должен быть не длиннее 32 символов'**
  String get phoneMaxLength;

  /// No description provided for @emailAlreadyUsed.
  ///
  /// In ru, this message translates to:
  /// **'Эта электронная почта уже используется'**
  String get emailAlreadyUsed;

  /// No description provided for @registrationFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось создать аккаунт. Попробуйте ещё раз.'**
  String get registrationFailed;

  /// No description provided for @accountCreatedLogin.
  ///
  /// In ru, this message translates to:
  /// **'Аккаунт создан. Теперь войдите.'**
  String get accountCreatedLogin;

  /// No description provided for @createAccount.
  ///
  /// In ru, this message translates to:
  /// **'Создать аккаунт'**
  String get createAccount;

  /// No description provided for @alreadyHaveAccountLogin.
  ///
  /// In ru, this message translates to:
  /// **'Уже есть аккаунт? Войти'**
  String get alreadyHaveAccountLogin;

  /// No description provided for @navHome.
  ///
  /// In ru, this message translates to:
  /// **'Главная'**
  String get navHome;

  /// No description provided for @navAppointments.
  ///
  /// In ru, this message translates to:
  /// **'Записи'**
  String get navAppointments;

  /// No description provided for @navProfile.
  ///
  /// In ru, this message translates to:
  /// **'Профиль'**
  String get navProfile;

  /// No description provided for @refresh.
  ///
  /// In ru, this message translates to:
  /// **'Обновить'**
  String get refresh;

  /// No description provided for @helloUser.
  ///
  /// In ru, this message translates to:
  /// **'Здравствуйте, {name}!'**
  String helloUser(String name);

  /// No description provided for @helloFallback.
  ///
  /// In ru, this message translates to:
  /// **'Здравствуйте!'**
  String get helloFallback;

  /// No description provided for @readyForVisit.
  ///
  /// In ru, this message translates to:
  /// **'Готовы запланировать следующий визит?'**
  String get readyForVisit;

  /// No description provided for @findConvenientTime.
  ///
  /// In ru, this message translates to:
  /// **'Найдите удобное время'**
  String get findConvenientTime;

  /// No description provided for @chooseServiceSpecialistSlot.
  ///
  /// In ru, this message translates to:
  /// **'Выберите услугу, сотрудника и свободное время.'**
  String get chooseServiceSpecialistSlot;

  /// No description provided for @bookAppointment.
  ///
  /// In ru, this message translates to:
  /// **'Записаться'**
  String get bookAppointment;

  /// No description provided for @upcoming.
  ///
  /// In ru, this message translates to:
  /// **'Предстоящие'**
  String get upcoming;

  /// No description provided for @viewAll.
  ///
  /// In ru, this message translates to:
  /// **'Показать все'**
  String get viewAll;

  /// No description provided for @noUpcomingAppointments.
  ///
  /// In ru, this message translates to:
  /// **'Нет предстоящих записей'**
  String get noUpcomingAppointments;

  /// No description provided for @nextBookingAppearsHere.
  ///
  /// In ru, this message translates to:
  /// **'Следующая запись появится здесь.'**
  String get nextBookingAppearsHere;

  /// No description provided for @profile.
  ///
  /// In ru, this message translates to:
  /// **'Профиль'**
  String get profile;

  /// No description provided for @client.
  ///
  /// In ru, this message translates to:
  /// **'Клиент'**
  String get client;

  /// No description provided for @backend.
  ///
  /// In ru, this message translates to:
  /// **'Сервер'**
  String get backend;

  /// No description provided for @signOut.
  ///
  /// In ru, this message translates to:
  /// **'Выйти'**
  String get signOut;

  /// No description provided for @bookingStepService.
  ///
  /// In ru, this message translates to:
  /// **'Услуга'**
  String get bookingStepService;

  /// No description provided for @bookingStepSpecialist.
  ///
  /// In ru, this message translates to:
  /// **'Сотрудник'**
  String get bookingStepSpecialist;

  /// No description provided for @bookingStepDate.
  ///
  /// In ru, this message translates to:
  /// **'Дата'**
  String get bookingStepDate;

  /// No description provided for @bookingStepAvailability.
  ///
  /// In ru, this message translates to:
  /// **'Свободное время'**
  String get bookingStepAvailability;

  /// No description provided for @bookingStepReview.
  ///
  /// In ru, this message translates to:
  /// **'Подтверждение'**
  String get bookingStepReview;

  /// No description provided for @noServices.
  ///
  /// In ru, this message translates to:
  /// **'Нет услуг'**
  String get noServices;

  /// No description provided for @locationHasNoServices.
  ///
  /// In ru, this message translates to:
  /// **'В этом филиале нет активных услуг.'**
  String get locationHasNoServices;

  /// No description provided for @durationMinutes.
  ///
  /// In ru, this message translates to:
  /// **'{minutes} мин'**
  String durationMinutes(int minutes);

  /// No description provided for @noSpecialist.
  ///
  /// In ru, this message translates to:
  /// **'Нет доступных сотрудников'**
  String get noSpecialist;

  /// No description provided for @noSpecialistForService.
  ///
  /// In ru, this message translates to:
  /// **'В этом филиале сейчас никто не оказывает выбранную услугу.'**
  String get noSpecialistForService;

  /// No description provided for @availableSpecialist.
  ///
  /// In ru, this message translates to:
  /// **'Доступен для записи'**
  String get availableSpecialist;

  /// No description provided for @noTimesOnDate.
  ///
  /// In ru, this message translates to:
  /// **'На эту дату нет свободного времени'**
  String get noTimesOnDate;

  /// No description provided for @chooseAnotherDateHint.
  ///
  /// In ru, this message translates to:
  /// **'Выберите другую дату, чтобы найти свободное время.'**
  String get chooseAnotherDateHint;

  /// No description provided for @chooseAnotherDate.
  ///
  /// In ru, this message translates to:
  /// **'Выбрать другую дату'**
  String get chooseAnotherDate;

  /// No description provided for @timesInTimezone.
  ///
  /// In ru, this message translates to:
  /// **'Время указано для часового пояса {timezone}'**
  String timesInTimezone(String timezone);

  /// No description provided for @serviceLabel.
  ///
  /// In ru, this message translates to:
  /// **'Услуга'**
  String get serviceLabel;

  /// No description provided for @specialistLabel.
  ///
  /// In ru, this message translates to:
  /// **'Сотрудник'**
  String get specialistLabel;

  /// No description provided for @dateLabel.
  ///
  /// In ru, this message translates to:
  /// **'Дата'**
  String get dateLabel;

  /// No description provided for @timeLabel.
  ///
  /// In ru, this message translates to:
  /// **'Время'**
  String get timeLabel;

  /// No description provided for @locationLabel.
  ///
  /// In ru, this message translates to:
  /// **'Филиал'**
  String get locationLabel;

  /// No description provided for @noteOptional.
  ///
  /// In ru, this message translates to:
  /// **'Комментарий (необязательно)'**
  String get noteOptional;

  /// No description provided for @bookingInProgress.
  ///
  /// In ru, this message translates to:
  /// **'Создаём запись…'**
  String get bookingInProgress;

  /// No description provided for @confirmBooking.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердить запись'**
  String get confirmBooking;

  /// No description provided for @myAppointments.
  ///
  /// In ru, this message translates to:
  /// **'Мои записи'**
  String get myAppointments;

  /// No description provided for @newAppointment.
  ///
  /// In ru, this message translates to:
  /// **'Новая запись'**
  String get newAppointment;

  /// No description provided for @past.
  ///
  /// In ru, this message translates to:
  /// **'Прошедшие'**
  String get past;

  /// No description provided for @cancelled.
  ///
  /// In ru, this message translates to:
  /// **'Отменённые'**
  String get cancelled;

  /// No description provided for @all.
  ///
  /// In ru, this message translates to:
  /// **'Все'**
  String get all;

  /// No description provided for @noAppointmentsInSection.
  ///
  /// In ru, this message translates to:
  /// **'В этом разделе пока нет записей.'**
  String get noAppointmentsInSection;

  /// No description provided for @bookServiceEmptyHint.
  ///
  /// In ru, this message translates to:
  /// **'Запишитесь на услугу, и визит появится здесь.'**
  String get bookServiceEmptyHint;

  /// No description provided for @bookNow.
  ///
  /// In ru, this message translates to:
  /// **'Записаться сейчас'**
  String get bookNow;

  /// No description provided for @noUpcomingSection.
  ///
  /// In ru, this message translates to:
  /// **'Нет предстоящих записей'**
  String get noUpcomingSection;

  /// No description provided for @noPastSection.
  ///
  /// In ru, this message translates to:
  /// **'Нет прошедших записей'**
  String get noPastSection;

  /// No description provided for @noCancelledSection.
  ///
  /// In ru, this message translates to:
  /// **'Нет отменённых записей'**
  String get noCancelledSection;

  /// No description provided for @noAllSection.
  ///
  /// In ru, this message translates to:
  /// **'Записей пока нет'**
  String get noAllSection;

  /// No description provided for @appointmentDetails.
  ///
  /// In ru, this message translates to:
  /// **'Детали записи'**
  String get appointmentDetails;

  /// No description provided for @cancelAppointmentQuestion.
  ///
  /// In ru, this message translates to:
  /// **'Отменить запись?'**
  String get cancelAppointmentQuestion;

  /// No description provided for @reasonOptional.
  ///
  /// In ru, this message translates to:
  /// **'Причина (необязательно)'**
  String get reasonOptional;

  /// No description provided for @keepAppointment.
  ///
  /// In ru, this message translates to:
  /// **'Оставить запись'**
  String get keepAppointment;

  /// No description provided for @cancelAppointment.
  ///
  /// In ru, this message translates to:
  /// **'Отменить запись'**
  String get cancelAppointment;

  /// No description provided for @appointmentBooked.
  ///
  /// In ru, this message translates to:
  /// **'Запись создана'**
  String get appointmentBooked;

  /// No description provided for @slotConfirmed.
  ///
  /// In ru, this message translates to:
  /// **'Выбранное время подтверждено в SlotBridge.'**
  String get slotConfirmed;

  /// No description provided for @timezoneLabel.
  ///
  /// In ru, this message translates to:
  /// **'Часовой пояс'**
  String get timezoneLabel;

  /// No description provided for @yourNote.
  ///
  /// In ru, this message translates to:
  /// **'Ваш комментарий'**
  String get yourNote;

  /// No description provided for @cancellationReason.
  ///
  /// In ru, this message translates to:
  /// **'Причина отмены'**
  String get cancellationReason;

  /// No description provided for @reschedule.
  ///
  /// In ru, this message translates to:
  /// **'Перенести'**
  String get reschedule;

  /// No description provided for @updating.
  ///
  /// In ru, this message translates to:
  /// **'Обновляем…'**
  String get updating;

  /// No description provided for @statusHistory.
  ///
  /// In ru, this message translates to:
  /// **'История статусов'**
  String get statusHistory;

  /// No description provided for @rescheduleTitle.
  ///
  /// In ru, this message translates to:
  /// **'Перенос записи'**
  String get rescheduleTitle;

  /// No description provided for @chooseNewDate.
  ///
  /// In ru, this message translates to:
  /// **'Выберите новую дату'**
  String get chooseNewDate;

  /// No description provided for @appointmentWithSpecialist.
  ///
  /// In ru, this message translates to:
  /// **'{service}, сотрудник — {employee}'**
  String appointmentWithSpecialist(String service, String employee);

  /// No description provided for @availableTimes.
  ///
  /// In ru, this message translates to:
  /// **'Свободное время'**
  String get availableTimes;

  /// No description provided for @availableTimesOnDate.
  ///
  /// In ru, this message translates to:
  /// **'Свободное время · {date}'**
  String availableTimesOnDate(String date);

  /// No description provided for @noAvailableTimes.
  ///
  /// In ru, this message translates to:
  /// **'Свободного времени нет. Выберите другую дату.'**
  String get noAvailableTimes;

  /// No description provided for @confirmNewTime.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердить новое время'**
  String get confirmNewTime;

  /// No description provided for @returnHome.
  ///
  /// In ru, this message translates to:
  /// **'Вернуться на главную'**
  String get returnHome;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ru'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ru':
      return AppLocalizationsRu();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
