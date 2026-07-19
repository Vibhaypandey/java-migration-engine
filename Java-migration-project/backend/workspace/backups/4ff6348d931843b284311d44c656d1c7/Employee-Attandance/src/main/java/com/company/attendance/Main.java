package com.company.attendance;

import com.company.attendance.model.Attendance;
import com.company.attendance.model.AttendanceStatus;
import com.company.attendance.model.Employee;
import com.company.attendance.repository.InMemoryAttendanceRepository;
import com.company.attendance.repository.InMemoryEmployeeRepository;
import com.company.attendance.service.*;

import java.time.LocalDate;
import java.time.LocalTime;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Map;
import java.util.Scanner;

public class Main {
    private static final Scanner scanner = new Scanner(System.in);
    private static EmployeeService employeeService;
    private static AttendanceService attendanceService;

    public static void main(String[] args) {
        InMemoryEmployeeRepository empRepo = new InMemoryEmployeeRepository();
        InMemoryAttendanceRepository attRepo = new InMemoryAttendanceRepository();
        employeeService = new EmployeeServiceImpl(empRepo);
        attendanceService = new AttendanceServiceImpl(attRepo, empRepo);

        while (true) {
            printMainMenu();
            int choice = readInt("Enter choice: ");
            switch (choice) {
                case 1: employeeMenu(); break;
                case 2: attendanceMenu(); break;
                case 3: System.out.println("Goodbye!"); return;
                default: System.out.println("Invalid choice.");
            }
        }
    }

    // ── Menus ──────────────────────────────────────────────────────────────────

    private static void printMainMenu() {
        System.out.println("\n===== Employee Attendance System =====");
        System.out.println("1. Employee Management");
        System.out.println("2. Attendance Management");
        System.out.println("3. Exit");
    }

    private static void employeeMenu() {
        System.out.println("\n--- Employee Management ---");
        System.out.println("1. Add Employee");
        System.out.println("2. View All Employees");
        System.out.println("3. View Employee by ID");
        System.out.println("4. Update Employee");
        System.out.println("5. Delete Employee");
        System.out.println("6. Back");

        int choice = readInt("Enter choice: ");
        try {
            switch (choice) {
                case 1: addEmployee(); break;
                case 2: viewAllEmployees(); break;
                case 3: viewEmployeeById(); break;
                case 4: updateEmployee(); break;
                case 5: deleteEmployee(); break;
                case 6: break;
                default: System.out.println("Invalid choice.");
            }
        } catch (Exception e) {
            System.out.println("Error: " + e.getMessage());
        }
    }

    private static void attendanceMenu() {
        System.out.println("\n--- Attendance Management ---");
        System.out.println("1. Mark Attendance");
        System.out.println("2. View Attendance by Employee");
        System.out.println("3. View Attendance by Date");
        System.out.println("4. Monthly Attendance Report");
        System.out.println("5. Back");

        int choice = readInt("Enter choice: ");
        try {
            switch (choice) {
                case 1: markAttendance(); break;
                case 2: viewAttendanceByEmployee(); break;
                case 3: viewAttendanceByDate(); break;
                case 4: monthlyReport(); break;
                case 5: break;
                default: System.out.println("Invalid choice.");
            }
        } catch (Exception e) {
            System.out.println("Error: " + e.getMessage());
        }
    }

    // ── Employee Actions ───────────────────────────────────────────────────────

    private static void addEmployee() {
        String id = readString("Employee ID: ");
        String name = readString("Name: ");
        String email = readString("Email: ");
        String dept = readString("Department: ");
        String desig = readString("Designation: ");
        Employee emp = employeeService.addEmployee(id, name, email, dept, desig);
        System.out.println("Added: " + emp);
    }

    private static void viewAllEmployees() {
        List<Employee> employees = employeeService.getAllEmployees();
        if (employees.isEmpty()) { System.out.println("No employees found."); return; }
        employees.forEach(System.out::println);
    }

    private static void viewEmployeeById() {
        String id = readString("Employee ID: ");
        System.out.println(employeeService.getEmployeeById(id));
    }

    private static void updateEmployee() {
        String id = readString("Employee ID to update: ");
        System.out.println("Leave blank to keep existing value.");
        String name = readString("New Name: ");
        String email = readString("New Email: ");
        String dept = readString("New Department: ");
        String desig = readString("New Designation: ");
        Employee emp = employeeService.updateEmployee(id,
                blankToNull(name), blankToNull(email), blankToNull(dept), blankToNull(desig));
        System.out.println("Updated: " + emp);
    }

    private static void deleteEmployee() {
        String id = readString("Employee ID to delete: ");
        employeeService.deleteEmployee(id);
        System.out.println("Employee " + id + " deleted.");
    }

    // ── Attendance Actions ─────────────────────────────────────────────────────

    private static void markAttendance() {
        String empId = readString("Employee ID: ");
        LocalDate date = readDate("Date (YYYY-MM-DD): ");
        AttendanceStatus status = readStatus();
        LocalTime checkIn = null, checkOut = null;
        if (status == AttendanceStatus.PRESENT) {
            checkIn = readTime("Check-in time (HH:MM): ");
            checkOut = readTime("Check-out time (HH:MM): ");
        }
        Attendance att = attendanceService.markAttendance(empId, date, status, checkIn, checkOut);
        System.out.println("Marked: " + att);
    }

    private static void viewAttendanceByEmployee() {
        String empId = readString("Employee ID: ");
        List<Attendance> list = attendanceService.getAttendanceByEmployee(empId);
        if (list.isEmpty()) { System.out.println("No attendance records found."); return; }
        list.forEach(System.out::println);
    }

    private static void viewAttendanceByDate() {
        LocalDate date = readDate("Date (YYYY-MM-DD): ");
        List<Attendance> list = attendanceService.getAttendanceByDate(date);
        if (list.isEmpty()) { System.out.println("No attendance records for this date."); return; }
        list.forEach(System.out::println);
    }

    private static void monthlyReport() {
        String empId = readString("Employee ID: ");
        int year = readInt("Year (e.g. 2024): ");
        int month = readInt("Month (1-12): ");
        Map<AttendanceStatus, Long> report = attendanceService.getMonthlyReport(empId, year, month);
        System.out.printf("Monthly Report for %s - %d/%02d%n", empId, year, month);
        for (AttendanceStatus s : AttendanceStatus.values()) {
            System.out.printf("  %-8s: %d%n", s, report.getOrDefault(s, 0L));
        }
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    private static String readString(String prompt) {
        System.out.print(prompt);
        return scanner.nextLine().trim();
    }

    private static int readInt(String prompt) {
        while (true) {
            System.out.print(prompt);
            try {
                return Integer.parseInt(scanner.nextLine().trim());
            } catch (NumberFormatException e) {
                System.out.println("Please enter a valid number.");
            }
        }
    }

    private static LocalDate readDate(String prompt) {
        while (true) {
            try { return LocalDate.parse(readString(prompt)); }
            catch (DateTimeParseException e) { System.out.println("Invalid date. Use YYYY-MM-DD."); }
        }
    }

    private static LocalTime readTime(String prompt) {
        while (true) {
            try { return LocalTime.parse(readString(prompt)); }
            catch (DateTimeParseException e) { System.out.println("Invalid time. Use HH:MM."); }
        }
    }

    private static AttendanceStatus readStatus() {
        while (true) {
            String input = readString("Status (PRESENT/ABSENT/LEAVE): ").toUpperCase();
            try { return AttendanceStatus.valueOf(input); }
            catch (IllegalArgumentException e) { System.out.println("Invalid status. Choose PRESENT, ABSENT, or LEAVE."); }
        }
    }

    private static String blankToNull(String s) {
        return (s == null || s.trim().isEmpty()) ? null : s;
    }
}
