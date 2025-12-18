package com.krish.jobquestbackend;
import org.bson.types.ObjectId;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
@Service
public class JobApplicationService {
    @Autowired
    private JobApplicationRepository jobApplicationRepository;

    // Đường dẫn folder lưu file (Bạn có thể đổi thành cấu hình trong application.properties)
    private final Path fileStorageLocation = Paths.get("/app/uploads").toAbsolutePath().normalize();

    public JobApplicationService() {
        try {
            Files.createDirectories(this.fileStorageLocation);
        } catch (Exception ex) {
            throw new RuntimeException("Could not create the directory where the uploaded files will be stored.", ex);
        }
    }

    // Hàm mới xử lý Upload File
    public JobApplication createJobApplicationWithFile(
            MultipartFile file, String jobId, String userId, String name, 
            String email, String phone, String qualification, String status, List<String> skills
    ) throws IOException {

        String fileName = StringUtils.cleanPath(file.getOriginalFilename());
        
        // Thêm UUID để tránh trùng tên file
        String uniqueFileName = UUID.randomUUID().toString() + "_" + fileName;

        // Lưu file vào ổ cứng (Folder uploads)
        Path targetLocation = this.fileStorageLocation.resolve(uniqueFileName);
        Files.copy(file.getInputStream(), targetLocation, StandardCopyOption.REPLACE_EXISTING);

        // Tạo object JobApplication
        JobApplication application = new JobApplication();
        application.setJobId(new ObjectId(jobId)); 
        application.setUserId(new ObjectId(userId));
        application.setName(name);
        application.setEmail(email);
        application.setPhone(phone);
        application.setQualification(qualification);
        application.setSkills(skills);
        application.setStatus(status);
        
        // Lưu đường dẫn file vào resumeLink (Để sau này tải về hoặc xem)
        // Trong thực tế bạn nên lưu URL đầy đủ (ví dụ: http://localhost:8080/uploads/...)
        application.setResumeLink("/uploads/" + uniqueFileName); 

        return jobApplicationRepository.save(application);
    }
    public List<JobApplication> allJobApplications() {
        return jobApplicationRepository.findAll();
    }

    public Optional<JobApplication> singleJobApplication(ObjectId jobId) {
        return jobApplicationRepository.findByJobId(jobId);
    }

    public JobApplication createJobApplication(JobApplication jobApplication) {
        return jobApplicationRepository.insert(jobApplication);
    }

    public JobApplication updateStatus(ObjectId applicationId, String newStatus) {
        JobApplication application = jobApplicationRepository.findById(applicationId).orElseThrow(() -> new RuntimeException("Job application not found"));

        application.setStatus(newStatus);
        jobApplicationRepository.save(application);
        return application;
    }
}
