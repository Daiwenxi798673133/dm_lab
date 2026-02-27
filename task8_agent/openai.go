package main

import (
	"context"
	"errors"
	"fmt"
	"os"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/components/model"
)

func createOpenAIChatModel(ctx context.Context) (model.ToolCallingChatModel, error) {
	key := os.Getenv("OPENAI_API_KEY")
	modelName := os.Getenv("OPENAI_MODEL_NAME")
	baseURL := os.Getenv("OPENAI_BASE_URL")

	if key == "" {
		return nil, errors.New("OPENAI_API_KEY is required")
	}
	if modelName == "" {
		return nil, errors.New("OPENAI_MODEL_NAME is required")
	}

	chatModel, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
		BaseURL: baseURL,
		Model:   modelName,
		APIKey:  key,
	})
	if err != nil {
		return nil, fmt.Errorf("create openai chat model failed: %w", err)
	}
	return chatModel, nil
}
