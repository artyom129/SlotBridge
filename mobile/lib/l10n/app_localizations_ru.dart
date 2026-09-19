// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appTitle => 'SlotBridge';

  @override
  String get back => 'Назад';

  @override
  String get tryAgain => 'Повторить';

  @override
  String get errorCouldNotLoadData => 'Не удалось загрузить данные';

  @override
  String get errorGeneric => 'Что-то пошло не так. Попробуйте ещё раз.';

  @override
  String get errorTimeout => 'Сервер не ответил вовремя. Попробуйте ещё раз.';

  @override
  String get errorConnection =>
      'Не удалось подключиться к SlotBridge. Проверьте адрес сервера и подключение.';

  @override
  String get errorInvalidCredentials =>
      'Неверная электронная почта или пароль.';

  @override
  String get errorAccessDenied => 'Недостаточно прав для этого действия.';

  @override
  String get errorNotFound => 'Запрошенные данные не найдены.';

  @override
  String get errorConflict =>
      'Данные изменились. Обновите экран и попробуйте ещё раз.';

  @override
  String get errorCheckData => 'Проверьте введённые данные.';

  @override
  String get errorSlotUnavailable =>
      'Это время только что заняли. Но мы нашли ближайшие свободные варианты.';

  @override
  String get errorBookingScope => 'Для записи недоступен активный филиал.';

  @override
  String get errorClientOnly =>
      'Мобильное приложение предназначено для клиентов.';

  @override
  String get errorNoActiveLocation => 'Нет доступного филиала для записи.';

  @override
  String get statusBooked => 'Запланирована';

  @override
  String get statusConfirmed => 'Подтверждена';

  @override
  String get statusInProgress => 'Выполняется';

  @override
  String get statusCompleted => 'Завершена';

  @override
  String get statusCancelled => 'Отменена';

  @override
  String get statusNoShow => 'Неявка';

  @override
  String get statusUnknown => 'Неизвестно';

  @override
  String get welcomeTitle => 'Добро пожаловать в SlotBridge';

  @override
  String get welcomeSubtitle =>
      'Записывайтесь и управляйте визитами в одном месте.';

  @override
  String get emailLabel => 'Электронная почта';

  @override
  String get passwordLabel => 'Пароль';

  @override
  String get confirmPasswordLabel => 'Подтвердите пароль';

  @override
  String get showPassword => 'Показать пароль';

  @override
  String get hidePassword => 'Скрыть пароль';

  @override
  String get enterValidEmail => 'Введите корректную электронную почту';

  @override
  String get enterEmail => 'Введите электронную почту';

  @override
  String get enterPassword => 'Введите пароль';

  @override
  String get signIn => 'Войти';

  @override
  String get noAccountRegister => 'Нет аккаунта? Зарегистрироваться';

  @override
  String get secureStorageHint =>
      'Данные авторизации надёжно хранятся в защищённом хранилище устройства.';

  @override
  String get createAccountTitle => 'Создайте аккаунт';

  @override
  String get createAccountSubtitle =>
      'Записывайтесь и управляйте визитами в SlotBridge.';

  @override
  String get firstNameLabel => 'Имя';

  @override
  String get lastNameLabel => 'Фамилия';

  @override
  String get phoneOptionalLabel => 'Телефон (необязательно)';

  @override
  String get enterFirstName => 'Введите имя';

  @override
  String get enterLastName => 'Введите фамилию';

  @override
  String get max100Characters => 'Не больше 100 символов';

  @override
  String get passwordMinLength => 'Пароль должен содержать минимум 8 символов';

  @override
  String get passwordMaxLength => 'Пароль должен быть не длиннее 128 символов';

  @override
  String get repeatPassword => 'Повторите пароль';

  @override
  String get passwordsDoNotMatch => 'Пароли не совпадают';

  @override
  String get phoneMaxLength => 'Телефон должен быть не длиннее 32 символов';

  @override
  String get emailAlreadyUsed => 'Эта электронная почта уже используется';

  @override
  String get registrationFailed =>
      'Не удалось создать аккаунт. Попробуйте ещё раз.';

  @override
  String get accountCreatedLogin => 'Аккаунт создан. Теперь войдите.';

  @override
  String get createAccount => 'Создать аккаунт';

  @override
  String get alreadyHaveAccountLogin => 'Уже есть аккаунт? Войти';

  @override
  String get navHome => 'Главная';

  @override
  String get navAppointments => 'Записи';

  @override
  String get navProfile => 'Профиль';

  @override
  String get refresh => 'Обновить';

  @override
  String helloUser(String name) {
    return 'Здравствуйте, $name!';
  }

  @override
  String get helloFallback => 'Здравствуйте!';

  @override
  String get readyForVisit => 'Готовы запланировать следующий визит?';

  @override
  String get findConvenientTime => 'Найдите удобное время';

  @override
  String get chooseServiceSpecialistSlot =>
      'Выберите услугу, сотрудника и свободное время.';

  @override
  String get bookAppointment => 'Записаться';

  @override
  String get upcoming => 'Предстоящие';

  @override
  String get viewAll => 'Показать все';

  @override
  String get noUpcomingAppointments => 'Нет предстоящих записей';

  @override
  String get nextBookingAppearsHere => 'Следующая запись появится здесь.';

  @override
  String get profile => 'Профиль';

  @override
  String get client => 'Клиент';

  @override
  String get backend => 'Сервер';

  @override
  String get signOut => 'Выйти';

  @override
  String get bookingStepService => 'Услуга';

  @override
  String get bookingStepSpecialist => 'Сотрудник';

  @override
  String get bookingStepDate => 'Дата';

  @override
  String get bookingStepAvailability => 'Свободное время';

  @override
  String get bookingStepReview => 'Подтверждение';

  @override
  String get noServices => 'Нет услуг';

  @override
  String get locationHasNoServices => 'В этом филиале нет активных услуг.';

  @override
  String durationMinutes(int minutes) {
    return '$minutes мин';
  }

  @override
  String get noSpecialist => 'Нет доступных сотрудников';

  @override
  String get noSpecialistForService =>
      'В этом филиале сейчас никто не оказывает выбранную услугу.';

  @override
  String get availableSpecialist => 'Доступен для записи';

  @override
  String get noTimesOnDate => 'На эту дату нет свободного времени';

  @override
  String get chooseAnotherDateHint =>
      'Выберите другую дату, чтобы найти свободное время.';

  @override
  String get chooseAnotherDate => 'Выбрать другую дату';

  @override
  String timesInTimezone(String timezone) {
    return 'Время указано для часового пояса $timezone';
  }

  @override
  String get serviceLabel => 'Услуга';

  @override
  String get specialistLabel => 'Сотрудник';

  @override
  String get dateLabel => 'Дата';

  @override
  String get timeLabel => 'Время';

  @override
  String get locationLabel => 'Филиал';

  @override
  String get noteOptional => 'Комментарий (необязательно)';

  @override
  String get bookingInProgress => 'Создаём запись…';

  @override
  String get confirmBooking => 'Подтвердить запись';

  @override
  String get myAppointments => 'Мои записи';

  @override
  String get newAppointment => 'Новая запись';

  @override
  String get past => 'Прошедшие';

  @override
  String get cancelled => 'Отменённые';

  @override
  String get all => 'Все';

  @override
  String get noAppointmentsInSection => 'В этом разделе пока нет записей.';

  @override
  String get bookServiceEmptyHint =>
      'Запишитесь на услугу, и визит появится здесь.';

  @override
  String get bookNow => 'Записаться сейчас';

  @override
  String get noUpcomingSection => 'Нет предстоящих записей';

  @override
  String get noPastSection => 'Нет прошедших записей';

  @override
  String get noCancelledSection => 'Нет отменённых записей';

  @override
  String get noAllSection => 'Записей пока нет';

  @override
  String get appointmentDetails => 'Детали записи';

  @override
  String get cancelAppointmentQuestion => 'Отменить запись?';

  @override
  String get reasonOptional => 'Причина (необязательно)';

  @override
  String get keepAppointment => 'Оставить запись';

  @override
  String get cancelAppointment => 'Отменить запись';

  @override
  String get appointmentBooked => 'Запись создана';

  @override
  String get slotConfirmed => 'Выбранное время подтверждено в SlotBridge.';

  @override
  String get timezoneLabel => 'Часовой пояс';

  @override
  String get yourNote => 'Ваш комментарий';

  @override
  String get cancellationReason => 'Причина отмены';

  @override
  String get reschedule => 'Перенести';

  @override
  String get updating => 'Обновляем…';

  @override
  String get statusHistory => 'История статусов';

  @override
  String get rescheduleTitle => 'Перенос записи';

  @override
  String get chooseNewDate => 'Выберите новую дату';

  @override
  String appointmentWithSpecialist(String service, String employee) {
    return '$service, сотрудник — $employee';
  }

  @override
  String get availableTimes => 'Свободное время';

  @override
  String availableTimesOnDate(String date) {
    return 'Свободное время · $date';
  }

  @override
  String get noAvailableTimes =>
      'Свободного времени нет. Выберите другую дату.';

  @override
  String get confirmNewTime => 'Подтвердить новое время';

  @override
  String get returnHome => 'Вернуться на главную';

  @override
  String get language => 'Язык';

  @override
  String get russian => 'Русский';

  @override
  String get english => 'English';

  @override
  String get theme => 'Тема';

  @override
  String get editProfile => 'Редактировать профиль';

  @override
  String get waitlist => 'Лист ожидания';

  @override
  String get about => 'О приложении';

  @override
  String get version => 'Версия';

  @override
  String get save => 'Сохранить';

  @override
  String get recommended => 'Рекомендуем';

  @override
  String get allAvailableTimes => 'Все свободные времена';

  @override
  String get bestOption => 'Лучший вариант';

  @override
  String get earliestAvailable => 'Ближайшее время';

  @override
  String get fillsGap => 'Заполняет окно';
}
