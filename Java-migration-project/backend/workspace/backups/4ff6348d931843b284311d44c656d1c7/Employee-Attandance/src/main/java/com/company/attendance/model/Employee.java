package com.company.attendance.model;

public class Employee {
    private String id;
    private String name;
    private String email;
    private String department;
    private String designation;

    public Employee(String id, String name, String email, String department, String designation) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.department = department;
        this.designation = designation;
    }

    public String getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }
    public String getDepartment() { return department; }
    public String getDesignation() { return designation; }

    public void setName(String name) { this.name = name; }
    public void setEmail(String email) { this.email = email; }
    public void setDepartment(String department) { this.department = department; }
    public void setDesignation(String designation) { this.designation = designation; }

    @Override
    public String toString() {
        return String.format("Employee[id=%s, name=%s, email=%s, dept=%s, designation=%s]",
                id, name, email, department, designation);
    }
}
