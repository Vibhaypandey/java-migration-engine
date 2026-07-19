package com.company.attendance.service;

import com.company.attendance.exception.EmployeeNotFoundException;
import com.company.attendance.model.Employee;
import com.company.attendance.repository.EmployeeRepository;
import com.company.attendance.util.Validator;

import java.util.List;

public class EmployeeServiceImpl implements EmployeeService {
    private final EmployeeRepository repository;

    public EmployeeServiceImpl(EmployeeRepository repository) {
        this.repository = repository;
    }

    @Override
    public Employee addEmployee(String id, String name, String email, String department, String designation) {
        Validator.requireNonBlank(id, "Employee ID");
        Validator.requireNonBlank(name, "Name");
        Validator.requireValidEmail(email);
        Validator.requireNonBlank(department, "Department");
        Validator.requireNonBlank(designation, "Designation");

        if (repository.existsById(id)) {
            throw new IllegalArgumentException("Employee with ID " + id + " already exists.");
        }
        Employee employee = new Employee(id, name, email, department, designation);
        repository.save(employee);
        return employee;
    }

    @Override
    public Employee getEmployeeById(String id) {
        return repository.findById(id)
                .orElseThrow(() -> new EmployeeNotFoundException(id));
    }

    @Override
    public List<Employee> getAllEmployees() {
        return repository.findAll();
    }

    @Override
    public Employee updateEmployee(String id, String name, String email, String department, String designation) {
        Employee employee = getEmployeeById(id);
        if (name != null && !name.isBlank()) employee.setName(name);
        if (email != null && !email.isBlank()) { Validator.requireValidEmail(email); employee.setEmail(email); }
        if (department != null && !department.isBlank()) employee.setDepartment(department);
        if (designation != null && !designation.isBlank()) employee.setDesignation(designation);
        repository.save(employee);
        return employee;
    }

    @Override
    public void deleteEmployee(String id) {
        if (!repository.existsById(id)) throw new EmployeeNotFoundException(id);
        repository.deleteById(id);
    }
}
