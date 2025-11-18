package com.krish.jobquestbackend;

import org.bson.types.ObjectId;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/jobs")
// @CrossOrigin(origins = "https://job-quest-client.vercel.app")
@CrossOrigin(origins = "*") // tạm thời

public class JobController {
    @Autowired
    private JobService jobService;

    @Autowired
    private RecruiterService recruiterService; // ⚡HANT ⭐ ⭐ ⭐ ⭐ ⭐

    @GetMapping
    public ResponseEntity<List<Job>> getAllJobs() {
        return new ResponseEntity<List<Job>>(jobService.allJobs(), HttpStatus.OK);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Optional<Job>> getSingleJob(@PathVariable ObjectId id) {
        return new ResponseEntity<Optional<Job>>(jobService.singleJob(id), HttpStatus.OK);
    }

    @PostMapping
    public ResponseEntity<Job> createJob(@RequestBody Job job) {
        Job savedJob = jobService.createJob(job);

        // 🔧 Nếu job có recruiterEmail thì thêm jobId vào recruiter tương ứng
        if (job.getRecruiterEmail() != null && !job.getRecruiterEmail().isEmpty()) {
            try {
                recruiterService.addJobToRecruiter(job.getRecruiterEmail(), savedJob.getId().toHexString());
            } catch (Exception e) {
                System.err.println("⚠️ Không thể thêm jobId vào recruiter: " + e.getMessage());
            }
        }

        return new ResponseEntity<>(savedJob, HttpStatus.CREATED);
    }
    // public ResponseEntity<Job> createJob(@RequestBody Job job) {
    //     return new ResponseEntity<Job>(jobService.createJob(job), HttpStatus.CREATED);
    // }

    @DeleteMapping("/{id}")
    public ResponseEntity<Job> deleteJob(@PathVariable String id) {
        ObjectId jobId = new ObjectId(id);
        return new ResponseEntity<Job>(jobService.deleteJob(jobId), HttpStatus.NO_CONTENT);
    }
}
