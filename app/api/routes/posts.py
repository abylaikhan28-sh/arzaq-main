# app/api/routes/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional

from app.db.session import get_db
from app.models.user import User
from app.models.post import Post, PostLike, PostComment
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostWithDetails,
    LikeResponse,
    CommentCreate,
    CommentResponse
)
from app.core.security import get_current_active_user
from app.services.cloudinary_service import cloudinary_service

router = APIRouter()


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new post"""

    new_post = Post(
        **post_data.dict(),
        author_id=current_user.id
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    # Add counts
    post_response = PostResponse.from_orm(new_post)
    post_response.likes_count = 0
    post_response.comments_count = 0

    return post_response


@router.get("/", response_model=List[PostWithDetails])
async def get_all_posts(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all posts with details"""

    # Get posts with counts
    posts_query = db.query(
        Post,
        func.count(PostLike.id).label('likes_count'),
        func.count(PostComment.id).label('comments_count')
    ).outerjoin(PostLike).outerjoin(PostComment).group_by(Post.id).order_by(desc(Post.created_at))

    posts_query = posts_query.limit(limit).offset(offset)
    results = posts_query.all()

    # Format response
    response = []
    for post, likes_count, comments_count in results:
        # Check if current user liked the post
        is_liked = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == current_user.id
        ).first() is not None

        # Get author name
        author = db.query(User).filter(User.id == post.author_id).first()

        # Get comments
        comments = db.query(PostComment, User.full_name).join(
            User, User.id == PostComment.author_id
        ).filter(
            PostComment.post_id == post.id
        ).all()

        comments_list = [
            CommentResponse(
                id=comment.id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                author_name=author_name,
                text=comment.text,
                created_at=comment.created_at
            )
            for comment, author_name in comments
        ]

        response.append(PostWithDetails(
            **post.__dict__,
            author_name=author.full_name if author else "Unknown",
            likes_count=likes_count,
            comments_count=comments_count,
            is_liked=is_liked,
            comments=comments_list
        ))

    return response


@router.get("/{post_id}", response_model=PostWithDetails)
async def get_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get post by ID"""

    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Get counts
    likes_count = db.query(PostLike).filter(PostLike.post_id == post_id).count()
    comments_count = db.query(PostComment).filter(PostComment.post_id == post_id).count()

    # Check if current user liked
    is_liked = db.query(PostLike).filter(
        PostLike.post_id == post_id,
        PostLike.user_id == current_user.id
    ).first() is not None

    # Get author
    author = db.query(User).filter(User.id == post.author_id).first()

    # Get comments
    comments = db.query(PostComment, User.full_name).join(
        User, User.id == PostComment.author_id
    ).filter(
        PostComment.post_id == post_id
    ).all()

    comments_list = [
        CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_name=author_name,
            text=comment.text,
            created_at=comment.created_at
        )
        for comment, author_name in comments
    ]

    return PostWithDetails(
        **post.__dict__,
        author_name=author.full_name if author else "Unknown",
        likes_count=likes_count,
        comments_count=comments_count,
        is_liked=is_liked,
        comments=comments_list
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete post (author or admin only)"""

    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Check permissions
    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts"
        )

    # Delete image from Cloudinary if exists
    if post.image:
        try:
            public_id = post.image.split('/')[-1].split('.')[0]
            cloudinary_service.delete_image(public_id)
        except:
            pass

    db.delete(post)
    db.commit()

    return None


@router.post("/{post_id}/like", response_model=LikeResponse)
async def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Toggle like on a post"""

    # Check if post exists
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Check if user already liked the post
    existing_like = db.query(PostLike).filter(
        PostLike.post_id == post_id,
        PostLike.user_id == current_user.id
    ).first()

    if existing_like:
        # Unlike
        db.delete(existing_like)
        db.commit()
        is_liked = False
    else:
        # Like
        new_like = PostLike(
            post_id=post_id,
            user_id=current_user.id
        )
        db.add(new_like)
        db.commit()
        is_liked = True

    # Get new likes count
    likes_count = db.query(PostLike).filter(PostLike.post_id == post_id).count()

    return {
        "success": True,
        "is_liked": is_liked,
        "likes_count": likes_count
    }


@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a comment on a post"""

    # Check if post exists
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Create comment
    new_comment = PostComment(
        post_id=post_id,
        author_id=current_user.id,
        text=comment_data.text
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return CommentResponse(
        id=new_comment.id,
        post_id=new_comment.post_id,
        author_id=new_comment.author_id,
        author_name=current_user.full_name,
        text=new_comment.text,
        created_at=new_comment.created_at
    )


@router.delete("/{post_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a comment (author or admin only)"""

    comment = db.query(PostComment).filter(
        PostComment.id == comment_id,
        PostComment.post_id == post_id
    ).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    # Check permissions
    if comment.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )

    db.delete(comment)
    db.commit()

    return None


@router.post("/upload-image")
async def upload_post_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload post image to Cloudinary"""

    result = await cloudinary_service.upload_image(file, folder="arzaq/posts")

    return {
        "success": True,
        "url": result["url"],
        "public_id": result["public_id"]
    }
