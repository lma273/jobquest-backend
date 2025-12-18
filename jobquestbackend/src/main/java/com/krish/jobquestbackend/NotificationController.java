package com.krish.jobquestbackend;

import org.bson.types.ObjectId;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/notifications")
@CrossOrigin(origins = "*")
public class NotificationController {
    
    @Autowired
    private NotificationService notificationService;

    // Tạo notification mới
    @PostMapping("/create")
    public ResponseEntity<Notification> createNotification(@RequestBody Map<String, String> payload) {
        String userId = payload.get("userId");
        String title = payload.get("title");
        String message = payload.get("message");
        String type = payload.get("type");
        String jobTitle = payload.get("jobTitle");
        String company = payload.get("company");
        
        Notification notification = notificationService.createNotification(userId, title, message, type, jobTitle, company);
        return new ResponseEntity<>(notification, HttpStatus.CREATED);
    }

    // Lấy tất cả notifications của user
    @GetMapping("/{userId}")
    public ResponseEntity<List<Notification>> getUserNotifications(@PathVariable String userId) {
        List<Notification> notifications = notificationService.getUserNotifications(userId);
        return new ResponseEntity<>(notifications, HttpStatus.OK);
    }

    // Lấy unread notifications
    @GetMapping("/{userId}/unread")
    public ResponseEntity<List<Notification>> getUnreadNotifications(@PathVariable String userId) {
        List<Notification> notifications = notificationService.getUnreadNotifications(userId);
        return new ResponseEntity<>(notifications, HttpStatus.OK);
    }

    // Đếm số unread
    @GetMapping("/{userId}/unread/count")
    public ResponseEntity<Map<String, Long>> getUnreadCount(@PathVariable String userId) {
        long count = notificationService.getUnreadCount(userId);
        return new ResponseEntity<>(Map.of("count", count), HttpStatus.OK);
    }

    // Đánh dấu 1 notification đã đọc
    @PostMapping("/{notificationId}/read")
    public ResponseEntity<Notification> markAsRead(@PathVariable String notificationId) {
        Notification notification = notificationService.markAsRead(new ObjectId(notificationId));
        return new ResponseEntity<>(notification, HttpStatus.OK);
    }

    // Đánh dấu tất cả đã đọc
    @PostMapping("/{userId}/read-all")
    public ResponseEntity<String> markAllAsRead(@PathVariable String userId) {
        notificationService.markAllAsRead(userId);
        return new ResponseEntity<>("All notifications marked as read", HttpStatus.OK);
    }
}
