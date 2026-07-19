package com.company.attendance.repository;

import com.company.attendance.model.Employee;

import java.util.*;

public class InMemoryEmployeeRepository implements EmployeeRepository {
    private final Map<String, Employee> store = new HashMap<>();

    @Override
    public void save(Employee employee) {
        store.put(employee.getId(), employee);
    }

    @Override
    public Optional<Employee> findById(String id) {
        return Optional.ofNullable(store.get(id));
    }

    @Override
    public List<Employee> findAll() {
        return new ArrayList<>(store.values());
    }

    @Override
    public void deleteById(String id) {
        store.remove(id);
    }

    @Override
    public boolean existsById(String id) {
        return store.containsKey(id);
    }
}
