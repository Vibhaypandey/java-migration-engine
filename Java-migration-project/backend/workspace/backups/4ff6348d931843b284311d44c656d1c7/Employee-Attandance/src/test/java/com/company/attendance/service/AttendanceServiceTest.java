package com.company.attendance.service;

import com.company.attendance.exception.DuplicateAttendanceException;
import com.company.attendance.exception.EmployeeNotFoundException;
import com.company.attendance.model.Attendance;
import com.company.attendance.model.AttendanceStatus;
import com.company.attendance.repository.InMemoryAttendanceRepository;
import com.company.attendance.repository.InMemoryEmployeeRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class AttendanceServiceTest {
    private AttendanceService attendanceService;
    private EmployeeService employeeService;

    private static final String EMP_ID = "E001";
    private static final LocalDate TODAY = LocalDate.of(2024, 6, 15);

    @BeforeEach
    void setUp() {
        InMemoryEmployeeRepository empRepo = new InMemoryEmployeeRepository();
        employeeService = new EmployeeServiceImpl(empRepo);
        attendanceService = new AttendanceServiceImpl(new InMemoryAttendanceRepository(), empRepo);
        employeeService.addEmployee(EMP_ID, "Alice", "alice@example.com", "Eng", "Dev");
    }

    @Test
    void markAttendance_present_success() {
        Attendance att = attendanceService.markAttendance(EMP_ID, TODAY, AttendanceStatus.PRESENT,
                LocalTime.of(9, 0), LocalTime.of(18, 0));
        assertEquals(EMP_ID, att.getEmployeeId());
        assertEquals(AttendanceStatus.PRESENT, att.getStatus());
    }

    @Test
    void markAttendance_absent_success() {
        Attendance att = attendanceService.markAttendance(EMP_ID, TODAY, AttendanceStatus.ABSENT, null, null);
        assertEquals(AttendanceStatus.ABSENT, att.getStatus());
    }

    @Test
    void markAttendance_duplicate_throwsException() {
        attendanceService.markAttendance(EMP_ID, TODAY, AttendanceStatus.PRESENT,
                LocalTime.of(9, 0), LocalTime.of(18, 0));
        assertThrows(DuplicateAttendanceException.class,
                () -> attendanceService.markAttendance(EMP_ID, TODAY, AttendanceStatus.PRESENT,
                        LocalTime.of(9, 0), LocalTime.of(18, 0)));
    }

    @Test
    void markAttendance_unknownEmployee_throwsException() {
        assertThrows(EmployeeNotFoundException.class,
                () -> attendanceService.markAttendance("GHOST", TODAY, AttendanceStatus.PRESENT, null, null));
    }

    @Test
    void getAttendanceByEmployee_returnsRecords() {
        attendanceService.markAttendance(EMP_ID, TODAY, AttendanceStatus.PRESENT,
                LocalTime.of(9, 0), LocalTime.of(18, 0));
        attendanceService.markAttendance(EMP_ID, TODAY.plusDays(1), AttendanceStatus.ABSENT, null, null);
        List<Attendance> records = attendanceService.getAttendanceByEmployee(EMP_ID);
        assertEquals(2, records.size());
    }

    @Test
    void getAttendanceByDate_returnsCorrectRecords() {
        employeeService.addEmployee("E002", "Bob", "bob@example.com", "HR", "Manager");
        attendanceService.markAttendance(EMP_ID, TODAY, AttendanceStatus.PRESENT,
                LocalTime.of(9, 0), LocalTime.of(18, 0));
        attendanceService.markAttendance("E002", TODAY, AttendanceStatus.LEAVE, null, null);
        List<Attendance> records = attendanceService.getAttendanceByDate(TODAY);
        assertEquals(2, records.size());
    }

    @Test
    void getMonthlyReport_correctCounts() {
        attendanceService.markAttendance(EMP_ID, LocalDate.of(2024, 6, 1), AttendanceStatus.PRESENT,
                LocalTime.of(9, 0), LocalTime.of(18, 0));
        attendanceService.markAttendance(EMP_ID, LocalDate.of(2024, 6, 2), AttendanceStatus.ABSENT, null, null);
        attendanceService.markAttendance(EMP_ID, LocalDate.of(2024, 6, 3), AttendanceStatus.LEAVE, null, null);
        attendanceService.markAttendance(EMP_ID, LocalDate.of(2024, 6, 4), AttendanceStatus.PRESENT,
                LocalTime.of(9, 0), LocalTime.of(18, 0));

        Map<AttendanceStatus, Long> report = attendanceService.getMonthlyReport(EMP_ID, 2024, 6);
        assertEquals(2L, report.get(AttendanceStatus.PRESENT));
        assertEquals(1L, report.get(AttendanceStatus.ABSENT));
        assertEquals(1L, report.get(AttendanceStatus.LEAVE));
    }

    @Test
    void getMonthlyReport_unknownEmployee_throwsException() {
        assertThrows(EmployeeNotFoundException.class,
                () -> attendanceService.getMonthlyReport("GHOST", 2024, 6));
    }
}
