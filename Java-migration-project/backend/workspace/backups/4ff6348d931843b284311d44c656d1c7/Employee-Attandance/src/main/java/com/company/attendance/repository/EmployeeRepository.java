package com.company.attendance.repository;

import com.company.attendance.model.Employee;

import java.util.List;
import java.util.Optional;

public interface EmployeeRepository {
    void save(Employee employee);
    Optional<Employee> findById(String id);
    List<Employee> findAll();
    void deleteById(String id);
    boolean existsById(String id);
}
