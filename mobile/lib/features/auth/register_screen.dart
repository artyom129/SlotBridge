import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/errors/app_exception.dart';
import '../../core/ui/widgets.dart';
import '../../l10n/l10n.dart';
import 'auth_controller.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  static final _emailPattern = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');

  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmation = true;

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) return;

    await ref
        .read(authControllerProvider.notifier)
        .register(
          firstName: _firstNameController.text,
          lastName: _lastNameController.text,
          email: _emailController.text,
          password: _passwordController.text,
          phone: _phoneController.text,
        );

    if (!mounted) return;
    final auth = ref.read(authControllerProvider);
    if (auth.hasValue && auth.value != null) {
      TextInput.finishAutofillContext();
      return;
    }

    final error = auth.error;
    if (error is AppException && error.code == 'registration_login_failed') {
      TextInput.finishAutofillContext();
      final messenger = ScaffoldMessenger.of(context);
      ref.read(authControllerProvider.notifier).clearError();
      context.go('/login');
      messenger.showSnackBar(
        SnackBar(content: Text(context.l10n.accountCreatedLogin)),
      );
    }
  }

  String? _validateName(String? value, String emptyMessage) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return emptyMessage;
    if (text.length > 100) return context.l10n.max100Characters;
    return null;
  }

  String? _validateEmail(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return context.l10n.enterEmail;
    if (!_emailPattern.hasMatch(text)) return context.l10n.enterValidEmail;
    return null;
  }

  String? _validatePassword(String? value) {
    final text = value ?? '';
    if (text.isEmpty) return context.l10n.enterPassword;
    if (text.length < 8) return context.l10n.passwordMinLength;
    if (text.length > 128) return context.l10n.passwordMaxLength;
    return null;
  }

  String? _validateConfirmation(String? value) {
    if ((value ?? '').isEmpty) return context.l10n.repeatPassword;
    if (value != _passwordController.text) {
      return context.l10n.passwordsDoNotMatch;
    }
    return null;
  }

  String _registrationError(Object error) {
    if (error is AppException) {
      if (error.code == 'registration_login_failed') {
        return context.l10n.accountCreatedLogin;
      }
      if (error.statusCode == 409) return context.l10n.emailAlreadyUsed;
    }
    final translated = readableError(context, error);
    return translated == context.l10n.errorGeneric
        ? context.l10n.registrationFailed
        : translated;
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) => SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(
              24,
              28,
              24,
              MediaQuery.viewInsetsOf(context).bottom + 24,
            ),
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minHeight: constraints.maxHeight - 52,
              ),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 440),
                  child: AutofillGroup(
                    child: Form(
                      key: _formKey,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Align(
                            child: Container(
                              width: 72,
                              height: 72,
                              decoration: BoxDecoration(
                                color: colorScheme.primary,
                                borderRadius: BorderRadius.circular(22),
                              ),
                              child: const Icon(
                                Icons.person_add_alt_1_rounded,
                                color: Colors.white,
                                size: 36,
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),
                          Text(
                            context.l10n.createAccountTitle,
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineSmall
                                ?.copyWith(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            context.l10n.createAccountSubtitle,
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodyLarge,
                          ),
                          const SizedBox(height: 32),
                          TextFormField(
                            key: const Key('registerFirstNameField'),
                            controller: _firstNameController,
                            textCapitalization: TextCapitalization.words,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.givenName],
                            decoration: InputDecoration(
                              labelText: context.l10n.firstNameLabel,
                              prefixIcon: const Icon(
                                Icons.person_outline_rounded,
                              ),
                            ),
                            validator: (value) => _validateName(
                              value,
                              context.l10n.enterFirstName,
                            ),
                          ),
                          const SizedBox(height: 14),
                          TextFormField(
                            key: const Key('registerLastNameField'),
                            controller: _lastNameController,
                            textCapitalization: TextCapitalization.words,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.familyName],
                            decoration: InputDecoration(
                              labelText: context.l10n.lastNameLabel,
                              prefixIcon: const Icon(Icons.badge_outlined),
                            ),
                            validator: (value) => _validateName(
                              value,
                              context.l10n.enterLastName,
                            ),
                          ),
                          const SizedBox(height: 14),
                          TextFormField(
                            key: const Key('registerEmailField'),
                            controller: _emailController,
                            keyboardType: TextInputType.emailAddress,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [
                              AutofillHints.username,
                              AutofillHints.email,
                            ],
                            decoration: InputDecoration(
                              labelText: context.l10n.emailLabel,
                              prefixIcon: const Icon(
                                Icons.mail_outline_rounded,
                              ),
                            ),
                            validator: _validateEmail,
                          ),
                          const SizedBox(height: 14),
                          TextFormField(
                            key: const Key('registerPhoneField'),
                            controller: _phoneController,
                            keyboardType: TextInputType.phone,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [
                              AutofillHints.telephoneNumber,
                            ],
                            decoration: InputDecoration(
                              labelText: context.l10n.phoneOptionalLabel,
                              prefixIcon: const Icon(Icons.phone_outlined),
                            ),
                            validator: (value) {
                              if ((value?.trim().length ?? 0) > 32) {
                                return context.l10n.phoneMaxLength;
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 14),
                          TextFormField(
                            key: const Key('registerPasswordField'),
                            controller: _passwordController,
                            obscureText: _obscurePassword,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.newPassword],
                            decoration: InputDecoration(
                              labelText: context.l10n.passwordLabel,
                              prefixIcon: const Icon(
                                Icons.lock_outline_rounded,
                              ),
                              suffixIcon: IconButton(
                                key: const Key('registerPasswordVisibility'),
                                tooltip: _obscurePassword
                                    ? context.l10n.showPassword
                                    : context.l10n.hidePassword,
                                onPressed: auth.isLoading
                                    ? null
                                    : () => setState(
                                        () => _obscurePassword =
                                            !_obscurePassword,
                                      ),
                                icon: Icon(
                                  _obscurePassword
                                      ? Icons.visibility_rounded
                                      : Icons.visibility_off_rounded,
                                ),
                              ),
                            ),
                            validator: _validatePassword,
                          ),
                          const SizedBox(height: 14),
                          TextFormField(
                            key: const Key('registerConfirmPasswordField'),
                            controller: _confirmPasswordController,
                            obscureText: _obscureConfirmation,
                            textInputAction: TextInputAction.done,
                            autofillHints: const [AutofillHints.newPassword],
                            onFieldSubmitted: (_) => _submit(),
                            decoration: InputDecoration(
                              labelText: context.l10n.confirmPasswordLabel,
                              prefixIcon: const Icon(Icons.lock_reset_rounded),
                              suffixIcon: IconButton(
                                key: const Key(
                                  'registerConfirmPasswordVisibility',
                                ),
                                tooltip: _obscureConfirmation
                                    ? context.l10n.showPassword
                                    : context.l10n.hidePassword,
                                onPressed: auth.isLoading
                                    ? null
                                    : () => setState(
                                        () => _obscureConfirmation =
                                            !_obscureConfirmation,
                                      ),
                                icon: Icon(
                                  _obscureConfirmation
                                      ? Icons.visibility_rounded
                                      : Icons.visibility_off_rounded,
                                ),
                              ),
                            ),
                            validator: _validateConfirmation,
                          ),
                          if (auth.hasError) ...[
                            const SizedBox(height: 14),
                            Semantics(
                              liveRegion: true,
                              child: Text(
                                _registrationError(auth.error!),
                                key: const Key('registerError'),
                                style: TextStyle(color: colorScheme.error),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ],
                          const SizedBox(height: 22),
                          FilledButton(
                            key: const Key('registerButton'),
                            onPressed: auth.isLoading ? null : _submit,
                            child: auth.isLoading
                                ? const SizedBox.square(
                                    dimension: 22,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2.5,
                                    ),
                                  )
                                : Text(context.l10n.createAccount),
                          ),
                          const SizedBox(height: 8),
                          TextButton(
                            key: const Key('registerLoginLink'),
                            onPressed: auth.isLoading
                                ? null
                                : () {
                                    ref
                                        .read(authControllerProvider.notifier)
                                        .clearError();
                                    context.go('/login');
                                  },
                            child: Text(context.l10n.alreadyHaveAccountLogin),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
