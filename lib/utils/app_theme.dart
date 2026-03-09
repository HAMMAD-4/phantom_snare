import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// App-wide dark cyberpunk theme for SentinelPrivacy.
class AppTheme {
  AppTheme._();

  // Brand colors
  static const Color primaryColor = Color(0xFF00E5FF);   // Cyan
  static const Color accentColor = Color(0xFF00FF87);    // Green
  static const Color dangerColor = Color(0xFFFF3D57);    // Red
  static const Color warningColor = Color(0xFFFFBF00);   // Amber
  static const Color surfaceColor = Color(0xFF0D1117);   // Dark navy
  static const Color cardColor = Color(0xFF161B22);      // Dark card
  static const Color borderColor = Color(0xFF30363D);    // Border

  // Module colors
  static const Color observerColor = Color(0xFF58A6FF);  // Blue
  static const Color shieldColor = Color(0xFF3FB950);    // Green
  static const Color deceptorColor = Color(0xFFE3B341);  // Yellow
  static const Color phantomColor = Color(0xFFBC8CFF);   // Purple
  static const Color vaultColor = Color(0xFF00E5FF);     // Cyan

  static ThemeData get darkTheme {
    final base = ThemeData.dark();
    return base.copyWith(
      useMaterial3: true,
      colorScheme: const ColorScheme.dark(
        primary: primaryColor,
        secondary: accentColor,
        error: dangerColor,
        surface: surfaceColor,
        onSurface: Colors.white,
      ),
      scaffoldBackgroundColor: surfaceColor,
      cardColor: cardColor,
      textTheme: GoogleFonts.sourceCodeProTextTheme(base.textTheme).copyWith(
        displayLarge: GoogleFonts.orbitron(
          color: Colors.white,
          fontWeight: FontWeight.bold,
        ),
        displayMedium: GoogleFonts.orbitron(
          color: Colors.white,
          fontWeight: FontWeight.bold,
        ),
        headlineLarge: GoogleFonts.orbitron(
          color: Colors.white,
          fontWeight: FontWeight.w600,
        ),
        headlineMedium: GoogleFonts.orbitron(
          color: primaryColor,
          fontWeight: FontWeight.w600,
        ),
        titleLarge: GoogleFonts.sourceCodePro(
          color: Colors.white,
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: GoogleFonts.sourceCodePro(color: Colors.white70),
        bodyMedium: GoogleFonts.sourceCodePro(color: Colors.white60),
        labelLarge: GoogleFonts.sourceCodePro(
          color: primaryColor,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: cardColor,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: GoogleFonts.orbitron(
          color: primaryColor,
          fontSize: 18,
          fontWeight: FontWeight.bold,
          letterSpacing: 2,
        ),
        iconTheme: const IconThemeData(color: primaryColor),
      ),
      cardTheme: CardTheme(
        color: cardColor,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: borderColor, width: 1),
        ),
      ),
      dividerTheme: const DividerThemeData(color: borderColor, thickness: 1),
      iconTheme: const IconThemeData(color: primaryColor),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: surfaceColor,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: GoogleFonts.sourceCodePro(
            fontWeight: FontWeight.bold,
            letterSpacing: 1.2,
          ),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? accentColor
              : Colors.white38,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? accentColor.withAlpha(80)
              : Colors.white12,
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: cardColor,
        labelStyle: GoogleFonts.sourceCodePro(fontSize: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: const BorderSide(color: borderColor),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: cardColor,
        selectedItemColor: primaryColor,
        unselectedItemColor: Colors.white38,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}
