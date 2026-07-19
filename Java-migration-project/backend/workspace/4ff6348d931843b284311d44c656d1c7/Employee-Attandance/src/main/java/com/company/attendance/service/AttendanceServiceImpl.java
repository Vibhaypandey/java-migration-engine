package com.company.attendance.service;

import com.company.attendance.exception.DuplicateAttendanceException;
import com.company.attendance.model.Attendance;
import com.company.attendance.model.AttendanceStatus;
import com.company.attendance.repository.AttendanceRepository;
import com.company.attendance.repository.EmployeeRepository;
import com.company.attendance.exception.EmployeeNotFoundException;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class AttendanceServiceImpl implements AttendanceService {
    private final AttendanceRepository attendanceRepository;
    private final EmployeeRepository employeeRepository;

    public AttendanceServiceImpl(AttendanceRepository attendanceRepository, EmployeeRepository employeeRepository) {
        this.attendanceRepository = attendanceRepository;
        this.employeeRepository = employeeRepository;
    }

    @Override
    public Attendance markAttendance(String employeeId, LocalDate date, AttendanceStatus status,
                                     LocalTime checkIn, LocalTime checkOut) {
        if (!employeeRepository.existsById(employeeId)) throw new EmployeeNotFoundException(employeeId);

        attendanceRepository.findByEmployeeIdAndDate(employeeId, date).ifPresent(a -> {
            throw new DuplicateAttendanceException(employeeId, date.toString());
        });

        Attendance attendance = new Attendance(employeeId, date, status, checkIn, checkOut);
        attendanceRepository.save(attendance);
        return attendance;
    }

    @Override
    public List<Attendance> getAttendanceByEmployee(String employeeId) {
        if (!employeeRepository.existsById(employeeId)) throw new EmployeeNotFoundException(employeeId);
        return attendanceRepository.findByEmployeeId(employeeId);
    }

    @Override
    public List<Attendance> getAttendanceByDate(LocalDate date) {
        return attendanceRepository.findByDate(date);
    }

    @Override
    public Map<AttendanceStatus, Long> getMonthlyReport(String employeeId, int year, int month) {
        if (!employeeRepository.existsById(employeeId)) throw new EmployeeNotFoundException(employeeId);
        return attendanceRepository.findByEmployeeId(employeeId).stream()
                .filter(a -> a.getDate().getYear() == year && a.getDate().getMonthValue() == month)
                .collect(Collectors.groupingBy(Attendance::getStatus, Collectors.counting()));
    }
}
