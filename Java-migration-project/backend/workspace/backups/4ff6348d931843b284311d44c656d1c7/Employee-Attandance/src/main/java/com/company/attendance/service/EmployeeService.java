package com.company.attendance.service;

import com.company.attendance.model.Employee;

import java.util.List;

public interface EmployeeService {
    Employee addEmployee(String id, String name, String email, String department, String designation);
    Employee getEmployeeById(String id);
    List<Employee> getAllEmployees();
    Employee updateEmployee(String id, String name, String email, String department, String designation);
    void deleteEmployee(String id);
}
