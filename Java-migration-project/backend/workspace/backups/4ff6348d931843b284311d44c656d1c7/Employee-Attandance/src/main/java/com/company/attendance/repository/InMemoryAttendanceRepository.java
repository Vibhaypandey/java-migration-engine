package com.company.attendance.repository;

import com.company.attendance.model.Attendance;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

public class InMemoryAttendanceRepository implements AttendanceRepository {
    private final List<Attendance> store = new ArrayList<>();

    @Override
    public void save(Attendance attendance) {
        store.add(attendance);
    }

    @Override
    public List<Attendance> findByEmployeeId(String employeeId) {
        return store.stream()
                .filter(a -> a.getEmployeeId().equals(employeeId))
                .collect(Collectors.toList());
    }

    @Override
    public List<Attendance> findByDate(LocalDate date) {
        return store.stream()
                .filter(a -> a.getDate().equals(date))
                .collect(Collectors.toList());
    }

    @Override
    public Optional<Attendance> findByEmployeeIdAndDate(String employeeId, LocalDate date) {
        return store.stream()
                .filter(a -> a.getEmployeeId().equals(employeeId) && a.getDate().equals(date))
                .findFirst();
    }
}
