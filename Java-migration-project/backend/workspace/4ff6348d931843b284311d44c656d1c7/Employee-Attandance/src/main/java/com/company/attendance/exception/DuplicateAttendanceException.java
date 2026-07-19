package com.company.attendance.exception;

public class DuplicateAttendanceException extends RuntimeException {
    public DuplicateAttendanceException(String employeeId, String date) {
        super("Attendance already marked for employee " + employeeId + " on " + date);
    }
}
