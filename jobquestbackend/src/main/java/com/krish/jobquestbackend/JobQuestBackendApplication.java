package com.krish.jobquestbackend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.ApplicationContext;
@SpringBootApplication
public class JobQuestBackendApplication {

	public static void main(String[] args) {
        ApplicationContext ctx = SpringApplication.run(JobQuestBackendApplication.class, args);
		// ⭐ THÊM ĐOẠN NÀY - in ra tất cả beans
        System.out.println("========== ALL BEANS ==========");
        String[] beanNames = ctx.getBeanDefinitionNames();
        for (String beanName : beanNames) {
            if (beanName.contains("Controller") || beanName.contains("controller")) {
                System.out.println("✅ Found: " + beanName);
            }
        }
        System.out.println("===============================");
	}

}
