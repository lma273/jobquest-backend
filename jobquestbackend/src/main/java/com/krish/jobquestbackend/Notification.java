package com.krish.jobquestbackend;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.bson.types.ObjectId;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;

@Document(collection = "notifications")
@Data
@AllArgsConstructor
@NoArgsConstructor
public class Notification {
    @Id
    private ObjectId id;
    
    private String userId; // Email hoặc ID của user nhận notification
    private String title;
    private String message;
    private String type; // "application_accepted", "application_rejected", etc.
    private boolean read;
    private LocalDateTime createdAt;
    
    // Metadata cho notification (job title, company, etc.)
    private String jobTitle;
    private String company;

    @JsonProperty("id")
    public String getIdString() {
        return id != null ? id.toHexString() : null;
    }
}
