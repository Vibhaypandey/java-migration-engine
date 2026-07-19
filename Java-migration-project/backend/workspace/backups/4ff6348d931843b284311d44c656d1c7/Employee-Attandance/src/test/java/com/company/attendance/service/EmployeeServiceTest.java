package com.company.attendance.service;

import com.company.attendance.exception.EmployeeNotFoundException;
import com.company.attendance.model.Employee;
import com.company.attendance.repository.InMemoryEmployeeRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class EmployeeServiceTest {
    private EmployeeService service;

    @BeforeEach
    void setUp() {
        service = new EmployeeServiceImpl(new InMemoryEmployeeRepository());
    }

    @Test
    void addEmployee_success() {
        Employee emp = service.addEmployee("E001", "Alice", "alice@example.com", "Engineering", "Developer");
        assertEquals("E001", emp.getId());
        assertEquals("Alice", emp.getName());
    }

    @Test
    void addEmployee_duplicateId_throwsException() {
        service.addEmployee("E001", "Alice", "alice@example.com", "Engineering", "Developer");
        assertThrows(IllegalArgumentException.class,
                () -> service.addEmployee("E001", "Bob", "bob@example.com", "HR", "Manager"));
    }

    @Test
    void addEmployee_invalidEmail_throwsException() {
        assertThrows(IllegalArgumentException.class,
                () -> service.addEmployee("E002", "Bob", "not-an-email", "HR", "Manager"));
    }

    @Test
    void addEmployee_blankName_throwsException() {
        assertThrows(IllegalArgumentException.class,
                () -> service.addEmployee("E003", "  ", "c@example.com", "IT", "Analyst"));
    }

    @Test
    void getEmployeeById_notFound_throwsException() {
        assertThrows(EmployeeNotFoundException.class, () -> service.getEmployeeById("UNKNOWN"));
    }

    @Test
    void getAllEmployees_returnsAll() {
        service.addEmployee("E001", "Alice", "alice@example.com", "Eng", "Dev");
        service.addEmployee("E002", "Bob", "bob@example.com", "HR", "Manager");
        List<Employee> all = service.getAllEmployees();
        assertEquals(2, all.size());
    }

    @Test
    void updateEmployee_updatesFields() {
        service.addEmployee("E001", "Alice", "alice@example.com", "Eng", "Dev");
        Employee updated = service.updateEmployee("E001", "Alice Smith", null, null, "Senior Dev");
        assertEquals("Alice Smith", updated.getName());
        assertEquals("Senior Dev", updated.getDesignation());
        assertEquals("alice@example.com", updated.getEmail()); // unchanged
    }

    @Test
    void deleteEmployee_removesEmployee() {
        service.addEmployee("E001", "Alice", "alice@example.com", "Eng", "Dev");
        service.deleteEmployee("E001");
        assertThrows(EmployeeNotFoundException.class, () -> service.getEmployeeById("E001"));
    }

    @Test
    void deleteEmployee_notFound_throwsException() {
        assertThrows(EmployeeNotFoundException.class, () -> service.deleteEmployee("GHOST"));
    }
}
