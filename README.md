# School Sphere

School Sphere is a cloud-based School Management System designed to simplify academic and administrative operations for students, teachers, and administrators.

**Version:** 1.0  
**Prepared By:** Yash Dhumal  
**Date:** July 2026

## Overview

The platform digitizes core school workflows, including:

- Student and teacher management
- Attendance tracking
- Assignment management and submission
- Examination and result publishing
- Notice board and announcements
- Fee management
- Secure authentication and role-based access
- Cloud deployment and mobile access

## Intended Users

- School Administrators
- Teachers
- Students
- Parents, in future scope
- Developers
- Test Engineers

## Technology Stack

| Layer | Technology |
| --- | --- |
| Mobile App | React Native + Expo |
| Language | TypeScript |
| Backend | FastAPI |
| Backend Language | Python |
| Database | MySQL |
| Cache | Redis |
| Task Queue | Celery |
| Authentication | JWT |
| Deployment | AWS |

## User Roles

### Student

Students can:

- Login
- View timetable
- View attendance
- Submit assignments
- View marks
- View notices
- Update profile

### Teacher

Teachers can:

- Login
- Mark attendance
- Upload assignments
- Publish marks
- Manage classes
- Send notices

### Administrator

Administrators can:

- Create users
- Manage classes
- Manage teachers
- Manage students
- Assign subjects
- Configure school settings
- View reports
- Monitor the system

## Functional Requirements

### Authentication

- **FR-1 User Login:** Authenticate users using JWT with email and password.
- **FR-2 Authorization:** Restrict APIs by role.
- **FR-3 Password Security:** Store passwords using secure hashing.

### Student Module

- **FR-4 Student Registration:** Admin can register students.
- **FR-5 Student Dashboard:** Students can view attendance, assignments, marks, notices, and timetable.
- **FR-6 Assignment Submission:** Students can upload files before the deadline.

### Teacher Module

- **FR-7 Attendance:** Teachers can mark, edit, and report attendance.
- **FR-8 Assignment Management:** Teachers can create assignments, set deadlines, and upload resources.
- **FR-9 Examination:** Teachers can enter marks and publish results.

### Administrator Module

- **FR-10 User Management:** Create, edit, and delete users.
- **FR-11 Class Management:** Create classes and assign teachers and students.
- **FR-12 Notice Management:** Create, schedule, and delete notices.

### Notification Module

- **FR-13 Notifications:** Notify users about assignments, exams, fees, attendance, and announcements.
- Celery handles asynchronous notification processing.

### Reports Module

- **FR-14 Reports:** Generate attendance, student, performance, and fee reports.

## Non-Functional Requirements

### Performance

- API response under 300 ms for cached endpoints
- Support 5,000+ concurrent users
- Use Redis cache for frequent requests

### Scalability

- Horizontal scaling with FastAPI, Redis, and Celery workers

### Security

- JWT authentication
- Password hashing
- Role-based access control
- HTTPS
- Input validation

### Reliability

- 99.9% uptime target
- Automatic retry for failed background tasks
- Centralized logging

### Maintainability

- Modular architecture
- Repository pattern
- Exception handling
- Logging
- Lazy loading

### Availability

- Hosted on AWS
- Auto restart
- Backup support
- Continuous deployment

## System Architecture

The system follows a client-server architecture:

- React Native + Expo mobile app communicates with the backend through REST APIs
- FastAPI serves as the backend API layer
- Redis supports caching and background job coordination
- Celery processes asynchronous tasks
- MySQL stores application data
- AWS hosts the production deployment

## Database Entities

### User

- id
- name
- email
- password
- role
- created_at

### Student

- student_id
- roll_no
- class
- section
- phone
- address

### Teacher

- teacher_id
- department
- qualification
- experience

### Attendance

- attendance_id
- student_id
- date
- status
- teacher_id

### Assignment

- assignment_id
- title
- description
- deadline
- teacher_id
- class_id

### Submission

- submission_id
- assignment_id
- student_id
- file_url
- submitted_at

### Examination

- exam_id
- subject
- date
- teacher_id

### Marks

- mark_id
- exam_id
- student_id
- marks
- grade

## API Specification

### Authentication

- `POST /login`
- `POST /refresh`
- `POST /logout`

### Student

- `GET /students`
- `GET /students/{id}`
- `POST /students`
- `PUT /students/{id}`
- `DELETE /students/{id}`

### Attendance

- `GET /attendance`
- `POST /attendance`
- `PUT /attendance/{id}`

### Assignments

- `GET /assignments`
- `POST /assignments`
- `POST /submit-assignment`

### Results

- `GET /results`
- `POST /results`

## Security Design

- JWT authentication
- Refresh tokens
- Password hashing
- RBAC
- API validation
- Secure headers
- HTTPS
- Rate limiting
- SQL injection protection
- XSS prevention

## Deployment Architecture

- React Native + Expo App
- AWS EC2
- FastAPI
- Redis
- Celery Worker
- MySQL Database

## Future Enhancements

- Parent dashboard
- AI performance analytics
- Face recognition attendance
- Video lecture integration
- Online fee payment gateway
- Push notifications
- School bus tracking
- QR-based student identity
- Timetable generator
- Multi-school SaaS support

## Expected Outcomes

- Reduced manual paperwork
- Faster attendance processing
- Secure user authentication
- Better academic tracking
- Scalable cloud deployment
- Improved communication among administrators, teachers, and students

## Project Highlights

- Scalable architecture built with FastAPI, Redis caching, and Celery workers
- Secure JWT-based authentication with role-based access control
- Optimized performance through caching and asynchronous processing
- Cross-platform React Native + Expo app for Android and iOS
- Production-ready AWS deployment with logging and modular design
