package com.company.attendance.service;

import com.company.attendance.model.Attendance;
import com.company.attendance.model.AttendanceStatus;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;

public interface AttendanceService {
    Attendance markAttendance(String employeeId, LocalDate date, AttendanceStatus status,
                              LocalTime checkIn, LocalTime checkOut);
    List<Attendance> getAttendanceByEmployee(String employeeId);
    List<Attendance> getAttendanceByDate(LocalDate date);
    Map<AttendanceStatus, Long> getMonthlyReport(String employeeId, int year, int month);
}
