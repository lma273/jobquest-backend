# =============================
# Stage 1: Build the Spring Boot app
# =============================
FROM maven:3.9.6-eclipse-temurin-17 AS builder

# Đặt đúng thư mục có pom.xml
WORKDIR /app

# Copy toàn bộ project con vào container
COPY jobquestbackend/ .

# Build application (skip tests)
RUN mvn clean package -DskipTests


# =============================
# Stage 2: Run the app
# =============================
FROM eclipse-temurin:17-jdk-alpine

WORKDIR /app

# Copy jar từ builder stage
COPY --from=builder /app/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
