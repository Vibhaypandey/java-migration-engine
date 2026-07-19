package com.company.attendance.repository;

import com.company.attendance.model.Attendance;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface AttendanceRepository {
    void save(Attendance attendance);
    List<Attendance> findByEmployeeId(String employeeId);
    List<Attendance> findByDate(LocalDate date);
    Optional<Attendance> findByEmployeeIdAndDate(String employeeId, LocalDate date);
}
