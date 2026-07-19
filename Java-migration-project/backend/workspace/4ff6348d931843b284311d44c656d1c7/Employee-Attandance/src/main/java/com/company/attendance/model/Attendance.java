package com.company.attendance.model;

import java.time.LocalDate;
import java.time.LocalTime;

public class Attendance {
    private String employeeId;
    private LocalDate date;
    private AttendanceStatus status;
    private LocalTime checkIn;
    private LocalTime checkOut;

    public Attendance(String employeeId, LocalDate date, AttendanceStatus status,
                      LocalTime checkIn, LocalTime checkOut) {
        this.employeeId = employeeId;
        this.date = date;
        this.status = status;
        this.checkIn = checkIn;
        this.checkOut = checkOut;
    }

    public String getEmployeeId() { return employeeId; }
    public LocalDate getDate() { return date; }
    public AttendanceStatus getStatus() { return status; }
    public LocalTime getCheckIn() { return checkIn; }
    public LocalTime getCheckOut() { return checkOut; }

    @Override
    public String toString() {
        return String.format("Attendance[empId=%s, date=%s, status=%s, checkIn=%s, checkOut=%s]",
                employeeId, date, status, checkIn, checkOut);
    }
}
